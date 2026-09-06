from fastapi import APIRouter
from fastapi.responses import Response


router = APIRouter()


FUT_BOOT_XML = """<?xml version="1.0" encoding="utf-8"?>
<FutCfg>
  <cfgVersion>1</cfgVersion>
  <futDlc>
    <fut12>
      <minorVersion>1</minorVersion>
      <bootString>fut12</bootString>
      <futNotAvailable>0</futNotAvailable>
      <revision>
        <futSubVersion>1</futSubVersion>
        <Language>
          <dimeUniqueId>1</dimeUniqueId>
          <size>1</size>
        </Language>
      </revision>
      <key>
        <dimeUniqueId>2</dimeUniqueId>
        <futKeyType>0</futKeyType>
      </key>
    </fut12>
  </futDlc>
</FutCfg>
"""


@router.get("/futBoot.xml")
def fut_boot():
    return Response(
        content=FUT_BOOT_XML,
        media_type="application/xml",
        headers={"Cache-Control": "no-store"},
    )