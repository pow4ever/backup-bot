# 🤖 Discord Backup Bot para Servidor de Ragnarok Online (rAthena)

Este bot de Discord automatiza el proceso de backup completo de un servidor de Ragnarok Online basado en **rAthena**. Realiza una copia de seguridad de las bases de datos MySQL/MariaDB y de los archivos del servidor, los comprime y los sube de forma segura a una VPS remota, gestionando también la retención de copias antiguas.


## ✨ Características

*   **Backup Automático Programado:** Se ejecuta diariamente a la hora que configures (ej. 4:00 AM UTC-3).
*   **Backup Manual:** Usa el comando `!backup` en Discord para iniciar un backup en cualquier momento (solo para administradores).
*   **Backup Completo:**
    *   📦 **Archivos del servidor:** Sincroniza toda la carpeta de `rAthena` mediante `rsync`.
    *   🗄️ **Bases de datos:** Realiza un `mysqldump` de cada base de datos especificada y las comprime con `gzip`.
*   **Almacenamiento Remoto:** Sube los backups a una VPS remota usando `rsync` sobre SSH con autenticación por contraseña (vía `sshpass`).
*   **Gestión de Retención:** Elimina automáticamente los backups en la VPS remota que tengan más de los días configurados.
*   **Notificaciones en Discord:** Informa del progreso y el resultado (éxito/error) del backup mediante un elegante embed.
*   **Limpieza Local:** Elimina los archivos temporales locales después de una subida exitosa para no ocupar espacio en el servidor de juego.

## 📋 Requisitos Previos

*   **Servidor de Ragnarok Online (Local):** Donde se ejecuta rAthena y el bot.
*   **VPS Remota:** Destino donde se almacenarán los backups.
*   **Bot de Discord:** Necesitas haber creado una aplicación/bot en el [Portal de Desarrolladores de Discord](https://discord.com/developers/applications) y tener su token.
*   **Dependencias del Sistema:** El script ejecuta comandos del sistema. Asegúrate de que los siguientes paquetes estén instalados en el servidor local:

    ```bash
    # En distribuciones basadas en Debian/Ubuntu
    sudo apt update
    sudo apt install python3 python3-pip mysql-client rsync sshpass -y
    ```


## 🚀 Instalación y Configuración

### 1. Clonar el repositorio y acceder al directorio

```bash
git clone https://github.com/pow4ever/backup-bot/
cd backup-bot
```

### 2. Configurar el Entorno Virtual de Python (Recomendado)

```bash
python3 -m venv venv
source venv/bin/activate  # En Linux/macOS
# .\venv\Scripts\activate  # En Windows (si pruebas localmente)
```

### 3. Instalar Dependencias de Python

El script necesita `discord.py` y `python-dotenv`. Instálalos con pip:

```bash
pip install discord.py python-dotenv
```

### 4. Configurar Variables de Entorno

Crea tu archivo de configuración a partir del ejemplo:

```bash
cp .env.example .env
```

Ahora, edita el archivo `.env` con tus datos. **¡Es crucial que rellenes toda la información correctamente!**

```dotenv
# ─── Discord ───────────────────────────────────────
# Token de tu bot de Discord
DISCORD_TOKEN=TU_TOKEN_DEL_BOT
# ID del canal de Discord donde el bot enviará los mensajes
DISCORD_CHANNEL_ID=123456789012345678

# ─── VPS Remota (destino del backup) ───────────────
REMOTE_HOST=tu.vps.remota.com
REMOTE_USER=root
REMOTE_PORT=22
REMOTE_PASSWORD=CONTRASEÑA_DE_TU_VPS
REMOTE_PATH=/root/backup

# ─── Servidor RO local ─────────────────────────────
RATHENA_PATH=/home/rathena
LOCAL_BACKUP_TMP=/tmp/ro_backups

# ─── Base de datos MariaDB del Servidor de Ragnarok ─
DB_HOST=localhost
DB_USER=usuario_bd
DB_PASSWORD=contraseña_bd
DB_NAMES=rathena_pre rathena_pre_logs

# ─── Retención de backups en VPS remota (días) ─────
RETENTION_DAYS=7

# ─── Horario automático (hora en formato 24h) ───────
# (UTC-3, ajusta según la zona horaria de tu servidor)
AUTO_BACKUP_HOUR=4
AUTO_BACKUP_MINUTE=0
```

> ⚠️ **Importante:** La seguridad de la contraseña de tu VPS en texto plano es un riesgo. Para un entorno de producción, considera usar [autenticación por clave SSH](#-mejoras-futuras--ideas) en lugar de `sshpass`.

### 5. Ejecutar el Bot

Con el entorno virtual activado y el archivo `.env` configurado, ejecuta el script:

```bash
python3 backup_bot.py
```

Deberías ver en la consola: `Bot conectado como NombreDeTuBot#1234` y un mensaje en el canal de Discord indicando que el bot está online.

Para mantenerlo corriendo incluso después de cerrar la sesión SSH, te recomendamos usar `screen`, `tmux` o crear un servicio `systemd`.


## 🎮 Uso del Bot

*   **`!backup`** (Solo administradores): Inicia un proceso de backup manual inmediatamente. El bot te responderá en el mismo canal con el progreso.
*   **Automático:** El bot se ejecutará a la hora programada (ej. 4:00 AM) y enviará el resultado al canal configurado.


## 📁 Estructura del Backup en la VPS Remota

Los backups se almacenan en la ruta que especificaste en `REMOTE_PATH` con la siguiente estructura:

```
/root/backup/
├── 20231027_040001/          # Carpeta con fecha y hora del backup (YYYYMMDD_HHMMSS)
│   ├── db/
│   │   ├── rathena_pre.sql.gz
│   │   └── rathena_pre_logs.sql.gz
│   └── files/                 # Copia de toda la carpeta /home/rathena
│       ├── conf/
│       ├── npc/
│       ├── save/
│       └── ...
├── 20231026_040002/
└── ...
```


## ⚙️ Personalización

*   **Más Bases de Datos:** Añade más nombres separados por espacios en la variable `DB_NAMES` del archivo `.env`.
*   **Cambiar la Hora del Backup:** Modifica `AUTO_BACKUP_HOUR` y `AUTO_BACKUP_MINUTE` en el `.env`. La hora es la del sistema donde se ejecuta el bot. Ajusta según tu zona horaria (UTC-3 en el ejemplo).
*   **Retención:** Cambia `RETENTION_DAYS` para mantener los backups más o menos tiempo.


## 🐛 Solución de Problemas

*   **Error de Conexión a la BD:** Verifica que `DB_HOST`, `DB_USER`, `DB_PASSWORD` sean correctos y que el usuario tenga permisos para hacer `mysqldump`. Prueba el comando manualmente en el servidor.
*   **Error de Conexión a la VPS Remota:**
    *   Confirma que `REMOTE_HOST`, `REMOTE_USER`, `REMOTE_PORT` y `REMOTE_PASSWORD` son correctos.
    *   Asegúrate de que el puerto SSH (ej. 22) esté abierto en el firewall de la VPS remota.
    *   Prueba conectarte manualmente con `sshpass -p 'tu_pass' ssh usuario@host -p puerto` desde el servidor local.
*   **El comando `!backup` no funciona:** Asegúrate de que el usuario que ejecuta el comando tiene permisos de administrador en el servidor de Discord.
*   **El bot no se conecta a Discord:** Verifica que el `DISCORD_TOKEN` es correcto y que el bot ha sido invitado a tu servidor.


## 📜 Licencia

Este proyecto está licenciado bajo la **GNU General Public License v3.0**.

Esto significa que eres **libre** de:
- Usar este script para cualquier propósito.
- Modificarlo y adaptarlo a tus necesidades.
- Compartirlo con quien quieras.

Pero siempre bajo la condición del **"Copyleft"** : Si distribuyes (compartes) el script, o cualquier versión modificada del mismo, **debes hacerlo bajo la misma licencia GPLv3**, manteniendo el aviso de copyright y garantizando que el código fuente siga siendo accesible.

El objetivo es asegurar que este software y todas sus futuras mejoras permanezcan siempre como **código abierto y libre para toda la comunidad**.

Para más detalles, consulta el archivo [LICENSE](LICENSE) o el texto oficial de la licencia: [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html).

**¡Que tus backups estén siempre a salvo!** 🛡️
