import logging
from pymongo.errors import DuplicateKeyError, OperationFailure

logger = logging.getLogger("charityflow.indexes")

async def create_indexes(db):
    """
    Creates database indexes safely and idempotently.
    Logs a warning if a unique index fails due to duplicates, without crashing the server.
    """
    # 1. users.email unique
    try:
        await db.users.create_index([("email", 1)], unique=True, name="idx_users_email_unique")
    except (DuplicateKeyError, OperationFailure) as e:
        logger.warning("Could not create unique index on users.email (duplicates exist or operation failed): %s", e)
    except Exception as e:
        logger.warning("Unexpected error creating users.email index: %s", e)

    # 2. ngos.email unique
    try:
        await db.ngos.create_index([("email", 1)], unique=True, name="idx_ngos_email_unique")
    except (DuplicateKeyError, OperationFailure) as e:
        logger.warning("Could not create unique index on ngos.email (duplicates exist or operation failed): %s", e)
    except Exception as e:
        logger.warning("Unexpected error creating ngos.email index: %s", e)

    # 3. donations (donor_email), (status), (created_at desc)
    try:
        await db.donations.create_index([("donor_email", 1)], name="idx_donations_donor_email")
        await db.donations.create_index([("status", 1)], name="idx_donations_status")
        await db.donations.create_index([("created_at", -1)], name="idx_donations_created_at_desc")
    except Exception as e:
        logger.warning("Error creating donations indexes: %s", e)

    # 4. logistics_entries (donation_id)
    try:
        await db.logistics_entries.create_index([("donation_id", 1)], name="idx_logistics_donation_id")
    except Exception as e:
        logger.warning("Error creating logistics_entries index: %s", e)

    # 5. contact_messages (email), (received_at)
    try:
        await db.contact_messages.create_index([("email", 1)], name="idx_contact_email")
        await db.contact_messages.create_index([("received_at", -1)], name="idx_contact_received_at")
    except Exception as e:
        logger.warning("Error creating contact_messages indexes: %s", e)

    # 6. activity_logs (user_email), (timestamp desc)
    try:
        await db.activity_logs.create_index([("user_email", 1)], name="idx_activity_user_email")
        await db.activity_logs.create_index([("timestamp", -1)], name="idx_activity_timestamp_desc")
    except Exception as e:
        logger.warning("Error creating activity_logs indexes: %s", e)

