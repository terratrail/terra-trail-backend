from rest_framework.renderers import JSONRenderer

class StandardResponseRenderer(JSONRenderer):
    """
    Custom renderer to standardize all successful API responses.
    Format:
    {
        "status": "success",
        "message": "...",
        "data": { ... }
    }
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response")

        # If data already has "status", it's likely handled by our exception handler
        # or manually formatted.
        if isinstance(data, dict) and "status" in data:
            return super().render(data, accepted_media_type, renderer_context)

        # Standardize success response
        message = "Operation successful"
        if isinstance(data, dict):
            # Extract message if explicitly provided in the response
            message = data.pop("message", message)
            # If the only thing left is the data, we might want to put it under "data"
            # However, if data is already large, we wrap it.
        
        standard_data = {
            "status": "success",
            "statusCode": response.status_code,
            "message": message,
            "data": data
        }

        # If it's a delete operation (204), we might not have data
        if response.status_code == 204:
            standard_data["data"] = None

        return super().render(standard_data, accepted_media_type, renderer_context)
