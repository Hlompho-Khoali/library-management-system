import os
from supabase import create_client


supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(
    supabase_url,
    supabase_key
)


def get_document_url(file_path, expiry_seconds=3600):
    if not file_path:
        return None

    try:
        response = supabase.storage.from_("id-documents").create_signed_url(
            file_path,
            expiry_seconds,
        )
        data = getattr(response, "data", None) or response

        if isinstance(data, dict):
            return data.get("signedURL") or data.get("url")

        return data
    except Exception:
        return None


def upload_id_document(file_data, file_path):
    """
    Upload an ID document to the private Supabase bucket.
    """

    response = supabase.storage.from_("id-documents").upload(
        file_path,
        file_data,
        {
            "content-type": "image/jpeg",
            "upsert": False
        }
    )

    return response

def test_storage():
    response = supabase.storage.list_buckets()
    return response