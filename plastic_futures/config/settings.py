"""
Global settings, brand constants, and app configuration.
"""

# ---------------------------------------------------------------------------
# Repsol brand palette
# ---------------------------------------------------------------------------
REPSOL_ORANGE   = "#FF6600"
REPSOL_MAGENTA  = "#D4006A"
REPSOL_BLUE     = "#003087"
IVORY           = "#FAFAF5"
IVORY_DARK      = "#F0F0E8"
DARK_NAVY       = "#1A1A2E"
SUCCESS_GREEN   = "#00B894"
WARNING_AMBER   = "#FDCB6E"
DANGER_RED      = "#E17055"
MID_GRAY        = "#8395A7"

# Plotly sequential colourscale using brand colours
COLORSCALE = [
    [0.0,  "#003087"],   # Repsol Blue  (low)
    [0.35, "#FF6600"],   # Orange       (mid-low)
    [0.65, "#D4006A"],   # Magenta      (mid-high)
    [1.0,  "#1A1A2E"],   # Dark navy    (high)
]

COLORSCALE_DIVERGING = [
    [0.0,  SUCCESS_GREEN],
    [0.5,  "#FAFAF5"],
    [1.0,  DANGER_RED],
]

# Fan-chart band colours (low opacity fills)
BAND_COLORS = {
    "95": "rgba(212, 0, 106, 0.10)",   # magenta  95 % CI
    "80": "rgba(255, 102, 0, 0.18)",   # orange   80 % CI
    "50": "rgba(0, 48, 135, 0.22)",    # blue     50 % CI
}
FORECAST_LINE_COLOR = REPSOL_ORANGE
HISTORY_LINE_COLOR  = REPSOL_BLUE

# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------
PAGE_CONFIG = dict(
    page_title="Plastic Futures Decision Hub",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE    = "Plastic Futures Decision Hub"
APP_SUBTITLE = "Compras & Planificación · Repsol"

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
