"""Audio-only Egress and authenticated access to private recording objects."""

import asyncio
from urllib.parse import quote

import httpx

from adit_voice_agent.services.calls import LiveKitGateway


class RecordingService:
    def __init__(self, settings):
        self.settings = settings

    async def start(self, call_id, room):
        from livekit import api
        key = f"calls/{call_id}/conversation.ogg"
        output = api.EncodedFileOutput(
            file_type=api.EncodedFileType.OGG, filepath=key, disable_manifest=True,
            s3=api.S3Upload(
                access_key=self.settings.s3_access_key.get_secret_value(),
                secret=self.settings.s3_secret_key.get_secret_value(),
                region=self.settings.s3_region, endpoint=self.settings.s3_endpoint,
                bucket=self.settings.recording_bucket, force_path_style=True,
            ),
        )
        async with LiveKitGateway(self.settings).client() as client:
            result = await client.egress.start_room_composite_egress(
                api.RoomCompositeEgressRequest(room_name=room, audio_only=True, file_outputs=[output])
            )
        return {"status": "recording", "egress_id": result.egress_id, "object_key": key}

    async def complete(self, recording):
        from livekit import api
        if not recording.get("egress_id"):
            return {**recording, "status": "missing"}
        async with LiveKitGateway(self.settings).client() as client:
            try:
                await client.egress.stop_egress(api.StopEgressRequest(egress_id=recording["egress_id"]))
            except api.TwirpError:
                pass  # The room ending may already have stopped Egress; inspect its real status below.
            for _ in range(12):
                response = await client.egress.list_egress(
                    api.ListEgressRequest(egress_id=recording["egress_id"])
                )
                if response.items:
                    item = response.items[0]
                    if item.status == api.EgressStatus.EGRESS_COMPLETE:
                        # Cloud Egress can return the singular file field instead of file_results.
                        file_info = item.file_results[0] if item.file_results else item.file
                        if file_info.size <= 0:
                            return {**recording, "status": "failed", "error": "Recording file is empty."}
                        return {**recording, "status": "ready", "size": file_info.size,
                                "duration_seconds": file_info.duration / 1_000_000_000 if file_info.duration else None,
                                "error": None}
                    if item.status in {api.EgressStatus.EGRESS_FAILED, api.EgressStatus.EGRESS_ABORTED, api.EgressStatus.EGRESS_LIMIT_REACHED}:
                        return {**recording, "status": "failed", "error": "Egress did not complete."}
                await asyncio.sleep(2)
        return {**recording, "status": "pending"}

    async def signed_url(self, recording, expires_in=300):
        if recording.get("status") != "ready":
            raise ValueError("Recording is not ready.")
        bucket = quote(self.settings.recording_bucket, safe="")
        key = quote(recording["object_key"], safe="/")
        secret = self.settings.supabase_service_role_key.get_secret_value()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/sign/{bucket}/{key}",
                headers={"Authorization": f"Bearer {secret}", "apikey": secret},
                json={"expiresIn": expires_in},
            )
            response.raise_for_status()
        signed = response.json()["signedURL"]
        return f"{self.settings.supabase_url.rstrip('/')}/storage/v1{signed}"
