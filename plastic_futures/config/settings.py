"""
Global settings, brand constants, and app configuration.
Minnesota Vikings colour theme.
"""

# ---------------------------------------------------------------------------
# Minnesota Vikings palette
# ---------------------------------------------------------------------------
REPSOL_ORANGE   = "#FFC62F"   # Vikings Gold  (primary accent)
REPSOL_MAGENTA  = "#7B5EA7"   # Vikings Medium Purple
REPSOL_BLUE     = "#4F2683"   # Vikings Deep Purple (primary)
IVORY           = "#F5F0FF"   # Light lavender background
IVORY_DARK      = "#EDE5FF"   # Slightly darker lavender
DARK_NAVY       = "#2D1154"   # Very dark purple
SUCCESS_GREEN   = "#00B894"   # Semantic green (universal)
WARNING_AMBER   = "#FFC62F"   # Gold doubles as warning
DANGER_RED      = "#E17055"   # Semantic red (universal)
MID_GRAY        = "#8395A7"   # Neutral gray

# Convenience aliases with explicit Vikings names
VIKINGS_PURPLE  = "#4F2683"
VIKINGS_GOLD    = "#FFC62F"
VIKINGS_MID     = "#7B5EA7"
VIKINGS_DARK    = "#2D1154"
VIKINGS_LIGHT   = "#F5F0FF"

# Plotly sequential colourscale: dark purple → medium purple → gold
COLORSCALE = [
    [0.0,  "#2D1154"],   # dark purple  (low)
    [0.40, "#4F2683"],   # deep purple  (mid-low)
    [0.70, "#7B5EA7"],   # medium purple(mid-high)
    [1.0,  "#FFC62F"],   # gold         (high)
]

COLORSCALE_DIVERGING = [
    [0.0,  SUCCESS_GREEN],
    [0.5,  "#F5F0FF"],
    [1.0,  DANGER_RED],
]

# Fan-chart band colours (low opacity fills)
BAND_COLORS = {
    "95": "rgba(79, 38, 131, 0.09)",    # purple  95 % CI
    "80": "rgba(255, 198, 47, 0.18)",   # gold    80 % CI
    "50": "rgba(45, 17, 84, 0.22)",     # dark purple 50 % CI
}
FORECAST_LINE_COLOR = REPSOL_ORANGE     # Gold forecast line
HISTORY_LINE_COLOR  = REPSOL_BLUE       # Purple history line

# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------
PAGE_CONFIG = dict(
    page_title="Plastic Futures Decision Hub",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE    = "Plastic Futures Decision Hub"
APP_SUBTITLE = "Compras & Planificación · Market Intelligence"

# Data history starts this year (demo data begins Jan 2015)
DATA_START_YEAR = 2015
DATA_END_YEAR   = 2024

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------
PRODUCTS = ["HDPE", "LDPE", "PP", "PVC", "PET", "PS"]

SUPPLIERS = ["SABIC", "BASF", "LyondellBasell", "Dow Chemical", "INEOS"]

REGIONS = ["Europa", "Asia-Pacífico", "Américas", "Oriente Medio"]

HORIZONS = {
    "1 mes":   1,
    "3 meses":  3,
    "6 meses":  6,
    "12 meses": 12,
    "18 meses": 18,
    "24 meses": 24,
}

SCENARIOS = ["Base", "Alcista (Bull)", "Bajista (Bear)", "Crisis energética", "Demanda débil"]

CHART_TYPES = ["Fan Chart", "Líneas", "Área", "Barras", "Heatmap"]

# Risk thresholds (0–100 scale)
RISK_LEVELS = {
    "Bajo":   (0,  33),
    "Medio":  (34, 66),
    "Alto":   (67, 100),
}

# Carrying cost for "buy now vs wait" (€/ton/month)
CARRYING_COST_PER_TON_MONTH = 8.0

# Typical purchase volume (tons) when none specified
DEFAULT_VOLUME_TONS = 500

# LLM model to use for insights
LLM_MODEL = "claude-haiku-4-5-20251001"
LLM_MAX_TOKENS = 1024

# Forecasting hyperparameters
FORECAST_QUANTILES = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
N_BOOTSTRAP        = 500    # bootstrap iterations for uncertainty
N_MONTE_CARLO      = 1000   # Monte-Carlo paths for scenario sim
BACKTEST_SPLITS    = 6      # walk-forward folds
