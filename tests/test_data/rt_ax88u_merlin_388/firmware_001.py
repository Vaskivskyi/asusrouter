"""Result of processing firmware_001.content."""

from asusrouter import AsusData

expected_result = {
    AsusData.FIRMWARE: {
        "webs_state_error": "0",
        "webs_state_info": "3004_388_4_0",
        "webs_state_info_beta": "",
        "webs_state_REQinfo": "",
        "webs_state_flag": "0",
        "webs_state_upgrade": "",
        "webs_state_level": "0",
        "sig_state_flag": "1",
        "sig_state_update": "0",
        "sig_state_upgrade": "1",
        "sig_state_error": "0",
        "sig_ver": "2.380",
        "cfg_check": "",
        "cfg_upgrade": "",
        "hndwr_status": "99",
        "state": True,
        "current": "None",
        "available": "3.0.0.4.388.4_0",
    }
}
