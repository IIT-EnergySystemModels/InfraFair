import pyam
import warnings

warnings.filterwarnings("ignore")

# set user name to get access to the scenario explorer
user_name = ''
user_password = ''

pyam.iiasa.set_config(user_name, user_password)

model_name = 'GENeSYS-MOD 1.0'
scenario_name = 'BAU'
region_name = 'World'

pyam.iiasa.Connection('openentrance')
# Reading data from openENTRANCE Platform
df = pyam.read_iiasa('openentrance', model = model_name, scenario = scenario_name)
#Power generation capacities for Spain
gen_cap = df.filter(region = 'Spain',variable = 'Capacity|Electricity|*', year = 2030).as_pandas()
gen_cap.head()

pyam.iiasa.Connection('openentrance')
# Reading data from openENTRANCE Platform
df = pyam.read_iiasa('openentrance', model = 'openTEPES 1.6.32', scenario = 'Baseline|SEP2030oE')
#Power transmission capacities for Spain
line_cap = df.as_pandas()
line_cap.head()
