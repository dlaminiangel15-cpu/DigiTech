from app import app, db
from sqlalchemy import text

def fix():
    with app.app_context():
        # Try to add the column directly via SQL
        try:
            db.session.execute(text("ALTER TABLE appointments ADD COLUMN qr_code_data VARCHAR(100)"))
            db.session.commit()
            print("Successfully added qr_code_data column.")
        except Exception as e:
            print(f"Column might already exist or error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix()
