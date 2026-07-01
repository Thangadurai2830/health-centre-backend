import logging

logger = logging.getLogger("app.otp")


async def send_otp_sms(mobile_number: str, country_code: str, otp_code: str) -> None:
    logger.info("Mock SMS to %s%s: your OTP is %s", country_code, mobile_number, otp_code)
