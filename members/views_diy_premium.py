import json
from django.views import View
from django.http import JsonResponse

class CalculatePremiumView(View):
    """API endpoint to calculate premium based on cover amount"""
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            cover_amount = float(data.get('cover_amount', 0))
            
            if cover_amount <= 0:
                return JsonResponse({'error': 'Invalid cover amount'}, status=400)
            
            # Simple premium calculation (1% of cover amount)
            premium = cover_amount * 0.01
            
            # Apply discounts for higher cover amounts
            if cover_amount > 50000:
                premium *= 0.9  # 10% discount for > R50k
            elif cover_amount > 30000:
                premium *= 0.95  # 5% discount for > R30k
            
            # Ensure minimum premium of R50
            premium = max(50, round(premium, 2))
            
            return JsonResponse({
                'premium': premium,
                'currency': 'ZAR',
                'frequency': 'monthly'
            })
            
        except (ValueError, TypeError) as e:
            return JsonResponse({'error': 'Invalid input data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'An error occurred while calculating premium'}, status=500)
