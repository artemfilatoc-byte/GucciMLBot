from urllib.parse import urlparse



import socks



from telethon import TelegramClient

from telethon.sessions.abstract import Session as TelethonSession



from core.config import TELETHON_CONNECT_TIMEOUT, get_telethon_credentials





def parse_proxy_url(proxy_url: str | None) -> tuple | None:

    if not proxy_url:

        return None

    url = proxy_url.strip()

    if not url:

        return None

                                                      

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()

    host = parsed.hostname

    port = parsed.port

    if not host or not port:

        return None

    username = parsed.username

    password = parsed.password

    proxy_type = socks.HTTP if scheme in ("http", "https") else socks.SOCKS5

                                            

    if username and password:

        return (proxy_type, host, port, True, username, password)

    return (proxy_type, host, port)





def build_telegram_client(

    session: TelethonSession, proxy_url: str | None = None

) -> TelegramClient:

    credentials = get_telethon_credentials()

    proxy = parse_proxy_url(proxy_url)

    kwargs: dict = {}

    if proxy is not None:

        kwargs["proxy"] = proxy

    return TelegramClient(

        session,

        credentials.api_id,

        credentials.api_hash,

        connection_retries=1,

        request_retries=1,

        timeout=TELETHON_CONNECT_TIMEOUT,

        device_model=credentials.device_model,

        system_version=credentials.system_version,

        app_version=credentials.app_version,

        lang_code=credentials.lang_code,

        system_lang_code=credentials.system_lang_code,

        **kwargs,

    )

