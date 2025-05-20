from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.shortcuts import get_object_or_404

import json
import random
import string
import datetime
import re
import pytesseract
from PIL import Image
import io
import base64
import openai

from .models_diy import DIYApplication, DIYApplicant

# Configure OpenAI API key
openai.api_key = settings.OPENAI_API_KEY

# Configure Tesseract path if needed
if hasattr(settings, 'TESSERACT_CMD'):
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


@require_POST
@csrf_exempt
def process_id_document(request):
    """Process an ID document using OCR to extract information"""
    try:
        # Get the uploaded image
        image_file = request.FILES.get('image')
        if not image_file:
            return JsonResponse({'error': 'No image provided'}, status=400)
        
        # Check file size (limit to 5MB)
        if image_file.size > 5 * 1024 * 1024:
            return JsonResponse({'error': 'File too large. Maximum size is 5MB'}, status=400)
        
        # Process the image with Tesseract OCR
        image = Image.open(image_file)
        text = pytesseract.image_to_string(image)
        
        # Extract information from OCR text
        result = {
            'id_number': extract_id_number(text),
            'full_name': extract_full_name(text),
            'date_of_birth': extract_date_of_birth(text),
            'gender': extract_gender(text),
        }
        
        return JsonResponse({'success': True, 'data': result})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@csrf_exempt
def validate_id_number(request):
    """Validate a South African ID number and extract information from it"""
    try:
        data = json.loads(request.body)
        id_number = data.get('id_number', '')
        
        if not id_number or len(id_number) != 13:
            return JsonResponse({'error': 'Invalid ID number format'}, status=400)
        
        # Validate ID number format (basic check)
        if not id_number.isdigit():
            return JsonResponse({'error': 'ID number must contain only digits'}, status=400)
        
        # Extract date of birth
        year = id_number[:2]
        month = id_number[2:4]
        day = id_number[4:6]
        
        # Determine century (19xx or 20xx)
        current_year = timezone.now().year % 100
        century = '19' if int(year) > current_year else '20'
        full_year = f"{century}{year}"
        
        try:
            date_of_birth = datetime.date(int(full_year), int(month), int(day))
            date_str = date_of_birth.strftime('%Y-%m-%d')
        except ValueError:
            return JsonResponse({'error': 'Invalid date in ID number'}, status=400)
        
        # Extract gender (7th digit: 0-4 = female, 5-9 = male)
        gender_digit = int(id_number[6])
        gender = 'female' if gender_digit < 5 else 'male'
        
        # TODO: Add checksum validation for more robust validation
        
        return JsonResponse({
            'is_valid': True,
            'date_of_birth': date_str,
            'gender': gender
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@csrf_exempt
def generate_otp(request):
    """Generate a 6-digit OTP for application verification"""
    try:
        data = json.loads(request.body)
        application_id = data.get('application_id')
        
        if not application_id:
            return JsonResponse({'error': 'Application ID is required'}, status=400)
        
        # Get the application
        application = get_object_or_404(DIYApplication, application_id=application_id)
        
        # Check if we can generate a new OTP (prevent abuse)
        if application.otp_generated_at:
            time_diff = timezone.now() - application.otp_generated_at
            if time_diff.total_seconds() < 60:  # 1 minute cooldown
                seconds_left = 60 - int(time_diff.total_seconds())
                return JsonResponse({
                    'error': f'Please wait {seconds_left} seconds before requesting a new OTP'
                }, status=429)
        
        # Generate a 6-digit OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Save OTP to application
        application.otp_code = otp
        application.otp_generated_at = timezone.now()
        application.otp_verified = False
        application.save()
        
        # Send OTP via SMS and email
        send_otp_to_user(application, otp)
        
        return JsonResponse({'success': True, 'message': 'OTP generated and sent'})
    
    except DIYApplication.DoesNotExist:
        return JsonResponse({'error': 'Application not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@csrf_exempt
def verify_otp(request):
    """Verify the OTP entered by the user"""
    try:
        data = json.loads(request.body)
        application_id = data.get('application_id')
        otp_code = data.get('otp_code')
        
        if not application_id or not otp_code:
            return JsonResponse({'error': 'Application ID and OTP code are required'}, status=400)
        
        # Get the application
        application = get_object_or_404(DIYApplication, application_id=application_id)
        
        # Check if OTP is expired (10 minutes validity)
        if application.otp_generated_at:
            time_diff = timezone.now() - application.otp_generated_at
            if time_diff.total_seconds() > 600:  # 10 minutes
                return JsonResponse({'error': 'OTP has expired. Please request a new one'}, status=400)
        
        # Check if OTP matches
        if application.otp_code != otp_code:
            # Increment attempts counter
            application.otp_attempts += 1
            application.save()
            
            # Check if max attempts reached
            if application.otp_attempts >= 3:
                return JsonResponse({
                    'error': 'Maximum attempts reached. Please request a new OTP'
                }, status=400)
            
            return JsonResponse({'error': 'Invalid OTP'}, status=400)
        
        # OTP is valid, mark as verified
        application.otp_verified = True
        application.save()
        
        return JsonResponse({'success': True, 'message': 'OTP verified successfully'})
    
    except DIYApplication.DoesNotExist:
        return JsonResponse({'error': 'Application not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@csrf_exempt
def ask_ai_about_plan(request):
    """Use OpenAI to answer questions about the plan using LegacyGuide"""
    try:
        data = json.loads(request.body)
        application_id = data.get('application_id')
        question = data.get('question')
        plan_id = data.get('plan_id')
        
        if not question:
            return JsonResponse({'error': 'Question is required'}, status=400)
        
        # Get the plan - either from application or directly from plan_id
        plan = None
        if application_id:
            try:
                application = get_object_or_404(DIYApplication, application_id=application_id)
                plan = application.plan
            except DIYApplication.DoesNotExist:
                return JsonResponse({'error': 'Application not found'}, status=404)
        elif plan_id:
            from schemes.models import Plan
            try:
                plan = Plan.objects.get(id=plan_id)
            except Plan.DoesNotExist:
                return JsonResponse({'error': 'Plan not found'}, status=404)
        else:
            return JsonResponse({'error': 'Either application_id or plan_id is required'}, status=400)
        
        if not plan:
            return JsonResponse({'error': 'No plan selected'}, status=400)
        
        # Get plan tiers for context
        plan_tiers = plan.plan_tiers.all()
        tiers_context = ""
        for tier in plan_tiers:
            tiers_context += f"\nTier: {tier.name}\n"
            tiers_context += f"  - Age Range: {tier.min_age} to {tier.max_age} years\n"
            tiers_context += f"  - Cover Amount: R{tier.cover_amount}\n"
        
        # Prepare context for the AI
        context = f"""
        Plan Name: {plan.name}
        Description: {plan.description}
        Premium: R{plan.premium}
        Main Cover: R{plan.main_cover}
        Waiting Period: {plan.waiting_period} months
        Spouses Allowed: {plan.spouses_allowed}
        Children Allowed: {plan.children_allowed}
        Extended Family Members Allowed: {plan.extended_allowed}
        {tiers_context}
        """
        
        # Add terms and conditions if available
        if hasattr(plan, 'terms_text') and plan.terms_text:
            context += f"\nTerms and Conditions:\n{plan.terms_text[:1000]}..."
        
        # Create system message for OpenAI
        system_message = """You are LegacyGuide, a helpful assistant for funeral insurance plans. You may explain plan features based on provided data, but you may not recommend or suggest which plan is best. Always reference the provided description, cover, or terms.
        
        You MAY:
        - Explain plan benefits, exclusions, and waiting periods
        - Clarify who is covered (main, spouse, children, extended)
        - Describe what terms like "cash payout" or "service benefit" mean
        - Answer questions based only on the plan information provided
        
        You may NOT:
        - Say "I recommend Plan A" or "This plan is best for you"
        - Choose a plan for the client
        - Provide any personal advice or suitability recommendation
        
        Keep your answers concise, accurate, and helpful.
        """
        
        # Call OpenAI API with the new Chat Completions endpoint
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Using GPT-4 for better compliance
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Here is information about a funeral plan:\n\n{context}\n\nQuestion: {question}"}
                ],
                max_tokens=300,
                temperature=0.7,
            )
            
            answer = response.choices[0].message["content"].strip()
        except Exception as api_error:
            # Fallback to older API if needed
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=f"{system_message}\n\nPLAN INFORMATION:\n{context}\n\nQUESTION: {question}\n\nANSWER:",
                max_tokens=300,
                n=1,
                stop=None,
                temperature=0.7,
            )
            
            answer = response.choices[0].text.strip()
        
        return JsonResponse({'success': True, 'answer': answer})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Helper functions

def extract_id_number(text):
    """Extract South African ID number from OCR text"""
    # Look for 13-digit number
    id_pattern = r'\b\d{13}\b'
    matches = re.findall(id_pattern, text)
    
    if matches:
        return matches[0]
    return None


def extract_full_name(text):
    """Extract full name from OCR text"""
    # This is a simplified approach - in a real system, you would need more sophisticated NLP
    lines = text.split('\n')
    for line in lines:
        # Look for lines with 2-3 words that might be names
        words = line.strip().split()
        if 2 <= len(words) <= 4:
            # Check if it doesn't contain digits
            if not any(char.isdigit() for char in line):
                return line.strip()
    return None


def extract_date_of_birth(text):
    """Extract date of birth from OCR text"""
    # Look for date patterns (YYYY-MM-DD, DD/MM/YYYY, etc.)
    date_patterns = [
        r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
        r'\b\d{2}/\d{2}/\d{4}\b',  # DD/MM/YYYY
        r'\b\d{2}\.\d{2}\.\d{4}\b',  # DD.MM.YYYY
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        if matches:
            return matches[0]
    
    return None


def extract_gender(text):
    """Extract gender from OCR text"""
    text_lower = text.lower()
    
    if 'male' in text_lower:
        return 'male'
    elif 'female' in text_lower:
        return 'female'
    
    return None


def send_otp_to_user(application, otp):
    """Send OTP to user via SMS and email"""
    try:
        applicant = application.applicant
        
        # Send SMS (mock implementation)
        print(f"Sending OTP {otp} to {applicant.phone_number}")
        
        # Send email
        subject = "Your Verification Code"
        message = f"Your verification code is: {otp}. This code will expire in 10 minutes."
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [applicant.email]
        
        # In a real implementation, you would use Django's send_mail function
        # send_mail(subject, message, from_email, recipient_list)
        
        return True
    except Exception as e:
        print(f"Error sending OTP: {str(e)}")
        return False
