except Exception as e:
            print(f"Error extracting audio: {str(e)}")
            return jsonify({"error": {"code": "AUDIO_EXTRACT_FAILED", "message": f"Failed to extract audio: {str(e)}"}}), 500