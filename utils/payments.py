import random
import string
import time

def generate_transaction_id():
    return "TX-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

def process_momo_payout(phone, amount):
    """
    MOCK implementation of MTN MoMo / Airtel Money Payout API.
    In production, this would use requests to POST to the provider's endpoint.
    """
    # Simulate network latency
    time.sleep(1)
    
    # Simple validation
    if not phone or len(phone) < 8:
        return {"success": False, "message": "Invalid mobile money number"}
    
    if amount <= 0:
        return {"success": False, "message": "Invalid payout amount"}
    
    # Simulate high success rate (95%)
    if random.random() < 0.95:
        return {
            "success": True,
            "transaction_id": generate_transaction_id(),
            "message": f"Successfully disbursed E{amount} to {phone} via MTN MoMo"
        }
    else:
        return {
            "success": False,
            "message": "Provider timeout. Please try again later."
        }

def process_bank_transfer(bank_details, amount):
    """
    MOCK implementation of a Bank Transfer API (e.g. Standard Bank or FNB).
    """
    time.sleep(1.5)
    
    if not bank_details.get('account_number'):
        return {"success": False, "message": "Missing bank account number"}
    
    return {
        "success": True,
        "transaction_id": generate_transaction_id(),
        "message": f"EFT for E{amount} initiated to {bank_details.get('bank_name')} ACC: {bank_details.get('account_number')}"
    }

def process_payout(user, amount, method):
    """
    Entry point for payroll payouts.
    """
    if method == 'MoMo':
        return process_momo_payout(user.momo_number, amount)
    elif method == 'Bank':
        details = {
            'bank_name': user.bank_name,
            'account_number': user.account_number
        }
        return process_bank_transfer(details, amount)
    else:
        # Cash/Manual
        return {
            "success": True,
            "transaction_id": "MANUAL-" + generate_transaction_id(),
            "message": "Manual payment recorded"
        }
