"""
Bulk import utilities for SchemeProduct CSV/XLSX parsing and validation.
"""
from decimal import Decimal, InvalidOperation
import io

import pandas as pd
from django.db.models import Q

from schemes.models import Plan


class BulkImportError:
    """Represents a single row validation error."""
    def __init__(self, row_num, field, message):
        self.row_num = row_num
        self.field = field
        self.message = message

    def __str__(self):
        return f"Row {self.row_num} ({self.field}): {self.message}"


class BulkImportResult:
    """Result of parsing and validating a bulk import file."""
    def __init__(self):
        self.rows = []  # list of valid {wholesale_plan_id, product_name, ...}
        self.errors = []  # list of BulkImportError
        self.summary = {}  # {total rows, valid rows, error count}


def parse_bulk_import_file(file_obj, branch):
    """
    Parse CSV or XLSX file and validate all rows.
    
    Returns BulkImportResult with parsed rows and any errors found.
    """
    result = BulkImportResult()
    
    try:
        # Determine file type and read
        filename = file_obj.name.lower()
        if filename.endswith('.csv'):
            df = pd.read_csv(file_obj)
        else:  # .xlsx or .xls
            df = pd.read_excel(file_obj)
    except Exception as e:
        result.errors.append(BulkImportError(0, 'file', f'Failed to read file: {str(e)}'))
        return result
    
    # Expected columns
    required_cols = {'wholesale_plan_id', 'product_name', 'retail_premium', 'client_cover_amount'}
    optional_cols = {'product_description', 'policy_type'}
    all_cols = required_cols | optional_cols
    
    # Validate headers
    df_cols = set(c.lower().strip() for c in df.columns)
    missing = required_cols - df_cols
    if missing:
        result.errors.append(
            BulkImportError(0, 'headers', f'Missing required columns: {", ".join(sorted(missing))}')
        )
        return result
    
    # Normalize column names
    df.columns = [c.lower().strip() for c in df.columns]
    
    # Process each row
    for idx, row in df.iterrows():
        row_num = idx + 2  # +2 because pandas is 0-indexed and row 1 is header
        row_errors = []
        
        # 1. Parse wholesale_plan_id
        try:
            plan_id = int(row.get('wholesale_plan_id', ''))
        except (ValueError, TypeError):
            result.errors.append(BulkImportError(row_num, 'wholesale_plan_id', 'Must be an integer'))
            continue
        
        # 2. Check plan exists and is wholesale
        try:
            plan = Plan.objects.get(
                pk=plan_id,
                is_wholesale=True,
                scheme__branch=branch,
                is_active=True,
            )
        except Plan.DoesNotExist:
            result.errors.append(
                BulkImportError(row_num, 'wholesale_plan_id', 
                               f'Plan {plan_id} not found, not wholesale, or not active in your branch')
            )
            continue
        
        # 3. Parse product_name
        product_name = (row.get('product_name', '') or '').strip()
        if not product_name:
            result.errors.append(BulkImportError(row_num, 'product_name', 'Required'))
            continue
        if len(product_name) > 200:
            result.errors.append(BulkImportError(row_num, 'product_name', 'Max 200 characters'))
            continue
        
        # 4. Parse product_description (optional)
        product_description = (row.get('product_description', '') or '').strip()
        
        # 5. Parse retail_premium
        try:
            retail_premium = Decimal(str(row.get('retail_premium', '')).strip())
            if retail_premium < 0:
                raise ValueError('Must be non-negative')
        except (InvalidOperation, ValueError, TypeError):
            result.errors.append(BulkImportError(row_num, 'retail_premium', 'Must be a valid decimal number'))
            continue
        
        # 6. Parse client_cover_amount
        try:
            client_cover = Decimal(str(row.get('client_cover_amount', '')).strip())
            if client_cover < 0:
                raise ValueError('Must be non-negative')
        except (InvalidOperation, ValueError, TypeError):
            result.errors.append(BulkImportError(row_num, 'client_cover_amount', 'Must be a valid decimal number'))
            continue
        
        # 7. Parse policy_type (optional, default 'service')
        policy_type = (row.get('policy_type', 'service') or 'service').strip().lower()
        if policy_type not in ('service', 'cash'):
            result.errors.append(BulkImportError(row_num, 'policy_type', 'Must be "service" or "cash"'))
            continue
        
        # Row is valid — add to result
        result.rows.append({
            'wholesale_plan': plan,
            'product_name': product_name,
            'product_description': product_description,
            'retail_premium': retail_premium,
            'client_cover_amount': client_cover,
            'policy_type': policy_type,
        })
    
    # Summary
    result.summary = {
        'total_rows': len(df),
        'valid_rows': len(result.rows),
        'error_count': len(result.errors),
    }
    
    return result


def create_products_from_import(onboarding, validated_rows):
    """
    Bulk create SchemeProduct instances from validated rows.
    Returns the list of created products.
    """
    products = []
    for row_data in validated_rows:
        product = SchemeProduct.objects.create(
            onboarding=onboarding,
            wholesale_plan=row_data['wholesale_plan'],
            product_name=row_data['product_name'],
            product_description=row_data['product_description'],
            retail_premium=row_data['retail_premium'],
            client_cover_amount=row_data['client_cover_amount'],
            policy_type=row_data['policy_type'],
        )
        products.append(product)
    return products
