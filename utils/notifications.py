from models import db, Notification

def send_notification(user_id=None, message="", role_target=None):
    """
    Persists a notification to the database for a specific user or a specific role.
    """
    notif = Notification(
        user_id=user_id,
        message=message,
        role_target=role_target
    )
    db.session.add(notif)
    db.session.commit()
    print(f"SAVED NOTIFICATION: {message}")
    return True

def notify_engineer_of_assignment(engineer_id, appointment_id):
    message = f"You have been assigned to Service Job #{appointment_id}."
    send_notification(user_id=engineer_id, message=message)

def notify_admin_of_booking(customer_name, appointment_id):
    message = f"New service booking SR-{appointment_id:05d} from {customer_name}."
    send_notification(role_target='admin', message=message)
