#!/bin/bash
# ========================================================
# SCRIPT DE INSTALACIÓN Y CONFIGURACIÓN PARA AWS EC2
# Compatible con Ubuntu 22.04/24.04 y Amazon Linux 2023
# ========================================================

set -e

echo "=== 1. Actualizando paquetes del sistema ==="
if [ -f /etc/debian_version ]; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git
elif [ -f /etc/redhat-release ] || [ -f /etc/system-release ]; then
    sudo dnf update -y
    sudo dnf install -y python3 python3-pip git
fi

echo "=== 2. Configurando Entorno Virtual Python ==="
python3 -m venv venv
source venv/bin/activate

echo "=== 3. Instalando dependencias de Python (FastAPI, uvicorn, boto3, psycopg2) ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== 4. Verificando archivo .env ==="
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[AVISO] Se ha creado el archivo .env a partir de .env.example."
    echo "[IMPORTANTE] Edita el archivo .env con: nano .env e introduce tu DATABASE_URL de RDS y nombres de buckets S3."
fi

echo "=== 5. Creando Servicio Systemd para ejecución continua ==="
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

SERVICE_FILE="/etc/systemd/system/videoplatform.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=VideoPlatform FastAPI Backend Service
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=$CURRENT_DIR/.env

[Install]
WantedBy=multi-user.target
EOF

echo "=== 6. Habilitando e iniciando el servicio ==="
sudo systemctl daemon-reload
sudo systemctl enable videoplatform
sudo systemctl restart videoplatform

echo "=== Estado del servicio ==="
sudo systemctl status videoplatform --no-pager

echo ""
echo "🎉 ¡Instalación completada exitosamente!"
echo "La API está corriendo en el puerto 8000."
echo "Para ver los logs en tiempo real ejecuta: sudo journalctl -u videoplatform -f"
