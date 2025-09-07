# credentials.py

"""
Quotex WebSocket credentials and headers
⚠️ Update SESSION + COOKIE often when they expire
"""

# ---------------------------
# Core WebSocket settings
QUOTEX_WS_URL = "wss://ws2.qxbroker.com/socket.io/"
QUOTEX_SOCKETIO_PATH = "socket.io"

# ---------------------------
# Auth session (replace when expired)
QUOTEX_SESSION_TOKEN = "7NAExENAl022xmhGV0teT7MaVC4G2NHvyVhukHIn"

# Account type: 0 = live, 1 = demo
QUOTEX_IS_DEMO = 0  

# Tournament ID (0 = none)
QUOTEX_TOURNAMENT_ID = 0  

# ---------------------------
# Headers & cookies (hardcoded for direct use)
QUOTEX_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
QUOTEX_ORIGIN = "https://qxbroker.com"
QUOTEX_COOKIE = (
    "lid=1527174; "
    "_ga=GA1.1.1555450310.1755431729; "
    "OTCTooltip={%22value%22:false}; "
    "z=[[%22graph%22%2C2%2C0%2C0%2C0.5630068]]; "
    "activeAccount=live; "
    "nas=[%22CADJPY%22%2C%22CADJPY_otc%22%2C%22EURNZD_otc%22%2C%22USDINR_otc%22%2C%22NZDCAD_otc%22]; "
    "cf_clearance=0Zc5PXTWBZEGmPwNyEWLCwi2VXMutwew81qas6G2b4Y-1757204025-1.2.1.1-VOgafYaaRV9HrlfRbwz1Li4g_Tb_2BrV7OEnaurapwCn_RPyow.elmvmunUy69EP_F7IITs44EMSX0zwr5oHwSkJygS97LymTh_wBXSUDhAdF3Az37mP_Wpfo_hoRzbaA4dztzZLzddyWQ4StbrTz2SMRTB460dxIPDdrSTGboJGx0Ag9SH9mDR_9NRpJjdpBDehX.IHHZJ2nAlbBkaA8sGBxszTZ.5FcjINtxYqMl4iYEBvc6WdeZz9eKf6YvlI; "
    "__cf_bm=TCJze5HMVa8iq4iCxKqVFNg0rEXyo8EQBcEcuGc4qFM-1757211205-1.0.1.1-WELKqbbfT0SEgf32T55vjVGNcmvzwkLIcuQeJ36uvVwI4gNjnIiZVibqd7ti.xI_DShKV_p2vln0QdejHvnVfMv0C9.PdDftpF8D31cgDyo; "
    "_cfuvid=FUZFmLBOLy2SFGWYRhaNUSKYR6of94.y68mRJAoMyPs-1757211205564-0.0.1.1-604800000; "
    "__vid_l3=7d9098c3-875b-4694-9690-8ba7f45e1356; "
    "_ga_L4T5GBPFHJ=GS2.1.s1757211205$o12$g1$t1757211232$j33$l0$h0"
)

# Full headers dict (ready for sio.connect)
QUOTEX_HEADERS = {
    "User-Agent": QUOTEX_USER_AGENT,
    "Origin": QUOTEX_ORIGIN,
    "Cookie": QUOTEX_COOKIE,
}
