from __future__ import annotations

import enum

class ProjectProfile(str, enum.Enum):
    EFH = "EFH"
    MFH_UNIT = "MFH_UNIT"  # one apartment/unit
    GEWERBE_BUERO = "GEWERBE_BUERO"
    GEWERBE_SHOP = "GEWERBE_SHOP"
    GEWERBE_WERKSTATT = "GEWERBE_WERKSTATT"
    GEWERBE_LAGER = "GEWERBE_LAGER"

class VariantKey(str, enum.Enum):
    STANDARD = "standard"
    KOMFORT = "komfort"
    PREMIUM = "premium"

class InstallType(str, enum.Enum):
    UP = "UP"       # Unterputz
    HW = "HW"       # Hohlwand
    AP = "AP"       # Aufputz
    MIX = "MIX"

class RenovationDepth(str, enum.Enum):
    LIGHT = "LIGHT"
    MEDIUM = "MEDIUM"
    HEAVY = "HEAVY"

class QuantitySource(str, enum.Enum):
    DEFAULTS = "DEFAULTS"
    PLAN_POINTS = "PLAN_POINTS"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"

class PlanFileType(str, enum.Enum):
    PDF = "pdf"
    JPG = "jpg"
    PNG = "png"

class CalcPolicy(str, enum.Enum):
    PROXY = "proxy"
    PLAN = "plan"
    HYBRID = "hybrid"

class ComplianceSeverity(str, enum.Enum):
    REQUIRED_FOR_SCOPE = "REQUIRED_FOR_SCOPE"
    RECOMMENDED = "RECOMMENDED"
    INFO = "INFO"

class ComplianceScope(str, enum.Enum):
    NEW_PARTS = "NEW_PARTS"
    NEW_DISTRIBUTION = "NEW_DISTRIBUTION"
    NEW_FINAL_CIRCUITS = "NEW_FINAL_CIRCUITS"
    EXISTING_UNCHANGED = "EXISTING_UNCHANGED"

class ComplianceStatus(str, enum.Enum):
    OPEN = "OPEN"
    IMPLEMENTED = "IMPLEMENTED"
    NOT_IN_SCOPE = "NOT_IN_SCOPE"
    EXISTING_CHECKED_OK = "EXISTING_CHECKED_OK"
    DEVIATION_DOCUMENTED = "DEVIATION_DOCUMENTED"
