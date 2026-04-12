from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger("terratrail")

def custom_exception_handler(exc, context):
    """
    Standardizes error responses across the entire API.
    Format:
    {
        "status": "error",
        "message": "Human readable message",
        "code": "error_code",
        "errors": { ... }
    }
    """
    # Call DRF's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            "status": "error",
            "statusCode": response.status_code,
            "message": "",
            "code": getattr(exc, "default_code", "error"),
            "errors": {}
        }

        # Extract messages
        if isinstance(response.data, dict):
            # If it's a dict, we might have specific field errors
            if "detail" in response.data:
                custom_response_data["message"] = response.data.pop("detail")
            
            # SimpleJWT specific
            if "messages" in response.data:
                msgs = response.data.pop("messages")
                if msgs and isinstance(msgs, list):
                    custom_response_data["message"] = msgs[0].get("message", "Authentication failed.")

            if "code" in response.data:
                custom_response_data["code"] = response.data.pop("code")

            # Anything else left in response.data goes into "errors"
            if response.data:
                custom_response_data["errors"] = response.data
                if not custom_response_data["message"]:
                    # Try to find a general message from field errors
                    first_key = next(iter(response.data))
                    first_val = response.data[first_key]
                    if isinstance(first_val, list) and first_val:
                        custom_response_data["message"] = f"Validation error: {first_val[0]}"
                    else:
                        custom_response_data["message"] = "A validation error occurred."
        
        elif isinstance(response.data, list):
            custom_response_data["message"] = response.data[0] if response.data else "An error occurred."
            custom_response_data["errors"] = {"non_field_errors": response.data}

        response.data = custom_response_data
    else:
        # Handle unhandled exceptions (500 errors)
        # In a real environment, you might log this
        logger.error(f"Unhandled Exception: {exc}", exc_info=True)
        return Response({
            "status": "error",
            "statusCode": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "An unexpected server error occurred.",
            "code": "server_error",
            "errors": {}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
