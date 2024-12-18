class FortniteCosmetic:
    cosmetidID: str
    name: str

    backendValue: str = "AthenaCharacter"
    rarityValue: str = "Common"

    icon: str
    small_icon: str

    is_banner: bool  = False
    unlocked_styles = {}

    is_exclusive: bool = False
    is_popular: bool = False