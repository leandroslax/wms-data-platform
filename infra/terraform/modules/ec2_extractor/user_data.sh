#!/bin/bash
set -euo pipefail

# ── Sistema ────────────────────────────────────────────────────────────────────
dnf update -y
dnf install -y \
  python3.11 python3.11-pip python3.11-devel \
  gcc gcc-c++ make \
  libaio \
  git \
  unzip \
  jq

# openfortivpn não está nos repos padrão do AL2023 — instala via EPEL
dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
dnf install -y openfortivpn

# ── Python deps ───────────────────────────────────────────────────────────────
python3.11 -m pip install --upgrade pip
python3.11 -m pip install \
  cx_Oracle \
  boto3 \
  pyarrow \
  pandas \
  pyiceberg[s3,glue] \
  python-dotenv

# ── Oracle Instant Client ──────────────────────────────────────────────────────
ORACLE_VERSION="21.13"
ORACLE_ZIP="instantclient-basiclite-linux.x64-$${ORACLE_VERSION}.0.0.0dbru.zip"
mkdir -p /opt/oracle
curl -fsSL \
  "https://download.oracle.com/otn_software/linux/instantclient/2113000/$${ORACLE_ZIP}" \
  -o "/tmp/$${ORACLE_ZIP}"
unzip -o "/tmp/$${ORACLE_ZIP}" -d /opt/oracle
ORACLE_HOME=$(ls -d /opt/oracle/instantclient_*)
echo "$${ORACLE_HOME}" > /etc/ld.so.conf.d/oracle-instantclient.conf
ldconfig

# ── Variáveis de ambiente Oracle ──────────────────────────────────────────────
cat >> /etc/environment <<EOF
LD_LIBRARY_PATH=$${ORACLE_HOME}
ORACLE_HOME=$${ORACLE_HOME}
EOF

# ── Usuário dedicado para o extrator ──────────────────────────────────────────
useradd -m -s /bin/bash extractor || true
mkdir -p /opt/wms-extractor
chown extractor:extractor /opt/wms-extractor

# ── systemd: serviço openfortivpn ─────────────────────────────────────────────
# Configuração preenchida via Secrets Manager no primeiro boot
# (ver script /opt/wms-extractor/setup_vpn.sh)
cat > /etc/systemd/system/wms-vpn.service <<'UNIT'
[Unit]
Description=WMS FortiVPN tunnel
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/opt/wms-extractor/.vpn.env
ExecStart=/usr/bin/openfortivpn \
  $${VPN_HOST}:$${VPN_PORT} \
  --username=$${VPN_USER} \
  --password=$${VPN_PASS} \
  --trusted-cert=$${VPN_CERT}
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
UNIT

# ── systemd: timer de extração (diário às 02h) ────────────────────────────────
cat > /etc/systemd/system/wms-extract.service <<'UNIT'
[Unit]
Description=WMS Oracle -> S3 extraction
After=wms-vpn.service
Requires=wms-vpn.service

[Service]
Type=oneshot
User=extractor
WorkingDirectory=/opt/wms-extractor
ExecStart=/usr/bin/python3.11 /opt/wms-extractor/export_oraint_parquet.py
StandardOutput=journal
StandardError=journal
UNIT

cat > /etc/systemd/system/wms-extract.timer <<'UNIT'
[Unit]
Description=Roda extrator WMS diariamente

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
UNIT

systemctl daemon-reload
systemctl enable wms-extract.timer
# VPN e timer são ativados após setup manual das credenciais

echo "Bootstrap concluido. Configure /opt/wms-extractor/.vpn.env e rode: systemctl enable --now wms-vpn wms-extract.timer"
