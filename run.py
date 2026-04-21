import os
from dotenv import load_dotenv
from app import create_app
from config import config_dict

# Load environment variables dari .env
load_dotenv()

# Ambil environment, default ke 'production'
env_name = os.environ.get('FLASK_ENV', 'production').lower()

# Ambil kelas config dari dictionary
config_class = config_dict.get(env_name, config_dict['default'])

# Factory App initialization
this_app = create_app(config_class)

if __name__ == '__main__':
    # Gunakan port dari env, default 80
    app_port = int(os.environ.get('FLASK_RUN_PORT', 80))
    this_app.run(host='0.0.0.0', port=app_port)