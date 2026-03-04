import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import asyncio
import os
import datetime


load_dotenv()

# ─── Config ──────────────────────────────────────────────────────────────────
TOKEN            = os.getenv("DISCORD_TOKEN")
CHANNEL_ID       = int(os.getenv("DISCORD_CHANNEL_ID"))

REMOTE_HOST      = os.getenv("REMOTE_HOST")
REMOTE_USER      = os.getenv("REMOTE_USER")
REMOTE_PORT      = os.getenv("REMOTE_PORT", "22")
REMOTE_PASSWORD  = os.getenv("REMOTE_PASSWORD")
REMOTE_PATH      = os.getenv("REMOTE_PATH", "/backups/ragnarok")

RATHENA_PATH     = os.getenv("RATHENA_PATH", "/home/ragnarok/rathena")
LOCAL_TMP        = os.getenv("LOCAL_BACKUP_TMP", "/tmp/ro_backups")

DB_HOST          = os.getenv("DB_HOST", "localhost")
DB_USER          = os.getenv("DB_USER", "ragnarok")
DB_PASSWORD      = os.getenv("DB_PASSWORD")
DB_NAMES         = os.getenv("DB_NAMES", "ragnarok ragnarok_log").split()

RETENTION_DAYS   = int(os.getenv("RETENTION_DAYS", "7"))
AUTO_HOUR        = int(os.getenv("AUTO_BACKUP_HOUR", "4"))
AUTO_MINUTE      = int(os.getenv("AUTO_MINUTE", "0"))
# ────────────────────────────────────────────────────────────────────────────


# ─── Async run_cmd (no bloquea) ─────────────────────────────────────────────
async def run_cmd(cmd: str) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode("utf‑8"), stderr.decode("utf‑8")
# ────────────────────────────────────────────────────────────────────────────


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


async def do_backup(ctx_or_channel):
    """Ejecuta el proceso completo de backup y reporta al canal de Discord."""
    channel = (
        ctx_or_channel
        if isinstance(ctx_or_channel, discord.TextChannel)
        else ctx_or_channel.channel
    )
    fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    local_dir = f"{LOCAL_TMP}/{fecha}"

    embed = discord.Embed(
        title="🗄️ Backup Ragnarok Online",
        description=f"Iniciando backup `{fecha}`...",
        color=discord.Color.yellow(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    msg = await channel.send(embed=embed)

    steps = []

    # 1. Crear directorio temporal local
    cmd_mkdir = f"mkdir -p {local_dir}/db {local_dir}/files"
    code, _, err = await run_cmd(cmd_mkdir)
    if code != 0:
        steps.append(f"❌ Crear directorios: {err[:80]}")
        return
    steps.append("✅ Directorios locales creados.")

    # 2. Backup de bases de datos (separado mysqldump + gzip)
    for db in DB_NAMES:
        dump_file = f"{local_dir}/db/{db}.sql"
        gz_file   = f"{local_dir}/db/{db}.sql.gz"

        # 2.1 mysqldump
        cmd_dump = (
            f"mysqldump --single-transaction --quick --skip-add-locks "
            f"-h {DB_HOST} -u {DB_USER} -p'{DB_PASSWORD}' {db} > {dump_file}"
        )
        code1, out1, err1 = await run_cmd(cmd_dump)
        if code1 != 0:
            steps.append(f"❌ DB `{db}` (dump): {err1[:80]}")
            continue

        # 2.2 gzip
        cmd_gzip = f"gzip {dump_file}"
        code2, _, err2 = await run_cmd(cmd_gzip)
        if code2 != 0:
            steps.append(f"❌ DB `{db}` (gzip): {err2[:80]}")
        else:
            steps.append(f"✅ DB `{db}`: OK")

    # 3. Backup de archivos rAthena
    cmd_rsync = f"rsync -avzh --delete {RATHENA_PATH}/ {local_dir}/files/"
    code, _, err = await run_cmd(cmd_rsync)
    if code != 0:
        steps.append(f"❌ Archivos rAthena: {err[:80]}")
    else:
        steps.append("✅ Archivos rAthena: OK")

    # 4. Subir a VPS remota con sshpass + rsync
    remote_dest = f"{REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}/{fecha}"
    cmd_upload = (
        f"sshpass -p '{REMOTE_PASSWORD}' rsync -avzh --delete "
        f"-e 'ssh -p {REMOTE_PORT} -o StrictHostKeyChecking=no' "
        f"{local_dir}/ {remote_dest}/"
    )
    code, _, err = await run_cmd(cmd_upload)
    if code != 0:
        steps.append(f"❌ Transferencia a VPS: {err[:80]}")
    else:
        steps.append("✅ Transferencia a VPS: OK")

    # 5. Limpieza local del tmp
    cmd_clean = f"rm -rf {local_dir}"
    await run_cmd(cmd_clean)
    steps.append("🧹 Limpieza local: OK")

    # 6. Eliminar backups antiguos en VPS remota
    cmd_cleanup = (
        f"sshpass -p '{REMOTE_PASSWORD}' ssh "
        f"-p {REMOTE_PORT} -o StrictHostKeyChecking=no "
        f"{REMOTE_USER}@{REMOTE_HOST} "
        f"\"find {REMOTE_PATH} -maxdepth 1 -type d -mtime +{RETENTION_DAYS} -exec rm -rf {{}} \\;\""
    )
    code, _, _ = await run_cmd(cmd_cleanup)
    if code != 0:
        steps.append(f"⚠️ Retención ({RETENTION_DAYS} días): revisar")
    else:
        steps.append("✅ Retención: OK")

    # 7. Actualizar embed con resultado
    all_ok = all(s.startswith("✅") or s.startswith("🧹") for s in steps)
    embed = discord.Embed(
        title="🗄️ Backup Ragnarok Online",
        description="\n".join(steps),
        color=discord.Color.green() if all_ok else discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.set_footer(
        text=f"Destino: {REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}/{fecha}"
    )
    await msg.edit(embed=embed)


# ── Comando manual: !backup ─────────────────────────────────────────────────
@bot.command(name="backup")
@commands.has_permissions(administrator=True)
async def backup_cmd(ctx):
    await do_backup(ctx)


# ── Tarea automática diaria ────────────────────────────────────────────────
@tasks.loop(time=datetime.time(hour=AUTO_HOUR, minute=AUTO_MINUTE))
async def auto_backup():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await do_backup(channel)


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    if not auto_backup.is_running():
        auto_backup.start()

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(
            embed=discord.Embed(
                title="✅ Backup Bot Online",
                description=(
                    f"Bot de backups activo.\n"
                    f"⏰ Backup automático: `{AUTO_HOUR:02}:{AUTO_MINUTE:02}` (hora servidor)\n"
                    f"📦 Destino: `{REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}`\n"
                    f"🗑️ Retención: `{RETENTION_DAYS} días`\n\n"
                    f"Usa `!backup` para forzar un backup manual."
                ),
                color=discord.Color.blurple(),
            )
        )


bot.run(TOKEN)