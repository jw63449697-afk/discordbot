from __future__ import annotations

import logging
import os
import re
import sqlite3
from datetime import date

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import database


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("contract_bot")
DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class ContractBot(commands.Bot):
    async def setup_hook(self) -> None:
        try:
            database.initialize_database()
            synced = await self.tree.sync()
            logger.info("슬래시 명령어 %s개를 동기화했습니다.", len(synced))
        except (sqlite3.Error, discord.HTTPException):
            logger.exception("데이터베이스 초기화 또는 명령어 동기화에 실패했습니다.")


intents = discord.Intents.default()
bot = ContractBot(command_prefix=commands.when_mentioned, help_command=None, intents=intents)


def make_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


async def reply_embed(
    interaction: discord.Interaction,
    embed: discord.Embed,
    *,
    ephemeral: bool = False,
) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


async def require_administrator(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        await reply_embed(
            interaction,
            make_embed("서버 전용 명령어", "이 명령어는 서버 안에서만 사용할 수 있습니다.", discord.Color.orange()),
            ephemeral=True,
        )
        return False
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
        await reply_embed(
            interaction,
            make_embed("권한 없음", "이 명령어는 서버 관리자만 사용할 수 있습니다.", discord.Color.red()),
            ephemeral=True,
        )
        return False
    return True


@bot.tree.command(name="계약추가", description="새 계약자를 계약 목록에 추가합니다.")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
@app_commands.describe(member="계약을 추가할 서버 멤버", start_date="계약 시작일 (YYYY-MM-DD)")
@app_commands.rename(member="사용자", start_date="날짜")
async def add_contract_command(
    interaction: discord.Interaction,
    member: discord.Member,
    start_date: str,
) -> None:
    if not await require_administrator(interaction):
        return
    if not DATE_PATTERN.fullmatch(start_date):
        await reply_embed(
            interaction,
            make_embed("날짜 형식 오류", "날짜는 YYYY-MM-DD 형식으로 입력해 주세요.", discord.Color.orange()),
            ephemeral=True,
        )
        return
    try:
        parsed_date = date.fromisoformat(start_date)
    except ValueError:
        await reply_embed(
            interaction,
            make_embed("날짜 형식 오류", "존재하는 날짜를 YYYY-MM-DD 형식으로 입력해 주세요.", discord.Color.orange()),
            ephemeral=True,
        )
        return

    try:
        added = database.add_contract(member.id, str(member), parsed_date.isoformat())
    except sqlite3.Error:
        logger.exception("계약 추가 중 데이터베이스 오류가 발생했습니다.")
        await reply_embed(
            interaction,
            make_embed("데이터베이스 오류", "계약을 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.", discord.Color.red()),
            ephemeral=True,
        )
        return

    if not added:
        await reply_embed(
            interaction,
            make_embed("이미 계약 중", f"{member.mention}님은 이미 계약 중입니다.", discord.Color.orange()),
            ephemeral=True,
        )
        return

    await reply_embed(
        interaction,
        make_embed(
            "계약이 추가되었습니다",
            f"대상: {member.mention}\n계약 시작일: {parsed_date.isoformat()}",
            discord.Color.green(),
        ),
    )


@bot.tree.command(name="계약취소", description="현재 계약을 종료하고 기록을 보존합니다.")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
@app_commands.describe(member="계약을 취소할 서버 멤버")
@app_commands.rename(member="사용자")
async def cancel_contract_command(
    interaction: discord.Interaction,
    member: discord.Member,
) -> None:
    if not await require_administrator(interaction):
        return

    try:
        start_date = database.cancel_contract(member.id)
    except sqlite3.Error:
        logger.exception("계약 취소 중 데이터베이스 오류가 발생했습니다.")
        await reply_embed(
            interaction,
            make_embed("데이터베이스 오류", "계약을 취소하지 못했습니다. 잠시 후 다시 시도해 주세요.", discord.Color.red()),
            ephemeral=True,
        )
        return

    if start_date is None:
        await reply_embed(
            interaction,
            make_embed("계약 없음", f"{member.mention}님은 현재 계약 중이 아닙니다.", discord.Color.orange()),
            ephemeral=True,
        )
        return

    await reply_embed(
        interaction,
        make_embed(
            "계약이 취소되었습니다",
            f"대상: {member.mention}\n계약 시작일: {start_date}\n계약 종료일: {date.today().isoformat()}",
            discord.Color.red(),
        ),
    )


@bot.tree.command(name="계약목록", description="현재 계약 중인 사람을 확인합니다.")
@app_commands.guild_only()
async def list_contracts_command(interaction: discord.Interaction) -> None:
    try:
        contracts = database.list_active_contracts()
    except sqlite3.Error:
        logger.exception("계약 목록 조회 중 데이터베이스 오류가 발생했습니다.")
        await reply_embed(
            interaction,
            make_embed("데이터베이스 오류", "계약 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.", discord.Color.red()),
            ephemeral=True,
        )
        return

    if not contracts:
        await reply_embed(
            interaction,
            make_embed("현재 계약 목록", "📋 현재 계약 중인 사람이 없습니다.", discord.Color.blurple()),
        )
        return

    entries = [
        f"🎨 <@{row['discord_user_id']}>\n계약 시작일: {row['contract_start_date']}"
        for row in contracts
    ]
    embeds: list[discord.Embed] = []
    current_entries: list[str] = []
    current_length = 0
    for entry in entries:
        if current_entries and current_length + len(entry) + 2 > 3800:
            embeds.append(
                make_embed("현재 계약 목록", "\n\n".join(current_entries), discord.Color.blurple())
            )
            current_entries = []
            current_length = 0
        current_entries.append(entry)
        current_length += len(entry) + 2

    final_description = "\n\n".join(current_entries)
    final_description += f"\n\n총 계약자: {len(contracts)}명"
    embeds.append(make_embed("현재 계약 목록", final_description, discord.Color.blurple()))

    await interaction.response.send_message(embed=embeds[0])
    for embed in embeds[1:]:
        await interaction.followup.send(embed=embed)


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    original_error = error.original if isinstance(error, app_commands.CommandInvokeError) else error
    if isinstance(original_error, discord.Forbidden):
        message = "봇에 메시지 전송 또는 Embed 표시 권한이 없습니다. 서버 권한을 확인해 주세요."
    elif isinstance(error, app_commands.TransformerError):
        message = "존재하는 서버 멤버를 선택해 주세요."
    elif isinstance(error, app_commands.CheckFailure):
        message = "이 명령어는 서버 안에서만 사용할 수 있습니다."
    else:
        logger.exception("처리되지 않은 슬래시 명령어 오류", exc_info=original_error)
        message = "명령어 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."

    try:
        await reply_embed(
            interaction,
            make_embed("명령어 오류", message, discord.Color.red()),
            ephemeral=True,
        )
    except discord.HTTPException:
        logger.exception("오류 안내 메시지를 전송하지 못했습니다.")


@bot.event
async def on_ready() -> None:
    if bot.user is not None:
        logger.info("%s로 로그인했습니다.", bot.user)


def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(".env 파일에 BOT_TOKEN을 설정해 주세요.")
    bot.run(token)


if __name__ == "__main__":
    main()
