import os
import shutil
import asyncio
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import discord
from config import AGY_PATH, DEFAULT_WORKSPACE
from email_service import send_email_async

# Resolve full binary path for Windows execution
AGY_EXE = shutil.which(AGY_PATH) or AGY_PATH

# Store active one-shot jobs: {job_id: dict}
active_jobs = {}

class AgentJob:
    def __init__(self, job_id: str, prompt: str, workspace: str, channel: discord.abc.Messageable, email_to: str = None):
        self.job_id = job_id
        self.prompt = prompt
        self.workspace = workspace if (workspace and os.path.isdir(workspace)) else DEFAULT_WORKSPACE
        self.channel = channel
        self.email_to = email_to
        self.start_time = None
        self.process = None
        self.status = "PENDING"
        self.output_lines = []
        self.status_message = None

    async def execute(self):
        self.status = "RUNNING"
        self.start_time = time.time()
        
        embed = discord.Embed(
            title="🤖 Antigravity Autonomous Agent Started",
            description=f"**Prompt:** {self.prompt[:400]}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Job ID", value=f"`{self.job_id}`", inline=True)
        embed.add_field(name="Workspace", value=f"`{self.workspace}`", inline=True)
        embed.add_field(name="Status", value="🔄 Initializing & Running...", inline=False)
        embed.set_footer(text="Running touchless agent task")
        
        try:
            self.status_message = await self.channel.send(embed=embed)
        except Exception:
            pass

        cmd = [
            AGY_EXE,
            "-p", self.prompt,
            "--dangerously-skip-permissions"
        ]

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self.workspace
            )

            last_update = time.time()
            full_output = []

            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    full_output.append(decoded)
                    self.output_lines.append(decoded)

                # Update Discord progress every 12 seconds
                if time.time() - last_update > 12 and self.status_message:
                    last_update = time.time()
                    elapsed = int(time.time() - self.start_time)
                    latest_snippet = "\n".join(full_output[-4:])
                    if len(latest_snippet) > 800:
                        latest_snippet = latest_snippet[-800:]
                    
                    update_embed = discord.Embed(
                        title="🤖 Antigravity Agent In Progress",
                        description=f"**Prompt:** {self.prompt[:300]}",
                        color=discord.Color.gold(),
                        timestamp=datetime.now()
                    )
                    update_embed.add_field(name="Job ID", value=f"`{self.job_id}`", inline=True)
                    update_embed.add_field(name="Elapsed Time", value=f"{elapsed}s", inline=True)
                    update_embed.add_field(
                        name="Live Progress",
                        value=f"```text\n{latest_snippet}\n```" if latest_snippet else "Executing operations...",
                        inline=False
                    )
                    try:
                        await self.status_message.edit(embed=update_embed)
                    except Exception:
                        pass

            await self.process.wait()
            return_code = self.process.returncode
            elapsed_total = round(time.time() - self.start_time, 1)

            final_text = "\n".join(full_output)
            self.status = "COMPLETED" if return_code == 0 else f"FAILED (Code: {return_code})"

            final_color = discord.Color.green() if return_code == 0 else discord.Color.red()
            done_embed = discord.Embed(
                title=f"✅ Agent Task Completed" if return_code == 0 else f"❌ Agent Task Failed",
                description=f"**Prompt:** {self.prompt[:300]}",
                color=final_color,
                timestamp=datetime.now()
            )
            done_embed.add_field(name="Status", value=self.status, inline=True)
            done_embed.add_field(name="Duration", value=f"{elapsed_total}s", inline=True)
            done_embed.add_field(name="Workspace", value=f"`{self.workspace}`", inline=False)

            snippet = final_text[-900:] if len(final_text) > 900 else final_text
            if not snippet:
                snippet = "Done (no console output produced)."
            done_embed.add_field(name="Output Summary", value=f"```text\n{snippet}\n```", inline=False)

            log_file = None
            if len(final_text) > 900:
                log_dir = Path(self.workspace) / ".agent_logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                log_path = log_dir / f"agent_job_{self.job_id}.log"
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(final_text)
                log_file = discord.File(str(log_path), filename=f"agent_job_{self.job_id}.log")

            if log_file:
                await self.channel.send(embed=done_embed, file=log_file)
            else:
                await self.channel.send(embed=done_embed)

            if self.email_to:
                subject = f"Antigravity Agent Report: Job {self.job_id}"
                body = (
                    f"<h2>Autonomous Agent Execution Report</h2>"
                    f"<p><b>Job ID:</b> {self.job_id}</p>"
                    f"<p><b>Status:</b> {self.status}</p>"
                    f"<p><b>Elapsed:</b> {elapsed_total}s</p>"
                    f"<p><b>Workspace:</b> {self.workspace}</p>"
                    f"<p><b>Prompt:</b><br/>{self.prompt}</p>"
                    f"<h3>Output Summary:</h3>"
                    f"<pre style='background:#f4f4f4;padding:10px;border-radius:5px;'>{snippet}</pre>"
                )
                email_attachments = [str(log_path)] if log_file else []
                await send_email_async(
                    to_email=self.email_to,
                    subject=subject,
                    html_content=body,
                    attachment_paths=email_attachments
                )

        except Exception as e:
            self.status = f"ERROR: {str(e)}"
            err_embed = discord.Embed(
                title="❌ Agent Execution Error",
                description=f"Error executing agent task: {str(e)}",
                color=discord.Color.red()
            )
            try:
                await self.channel.send(embed=err_embed)
            except Exception:
                pass
        finally:
            active_jobs.pop(self.job_id, None)

def launch_agent_task(prompt: str, workspace: str, channel: discord.abc.Messageable, email_to: str = None) -> str:
    job_id = f"job_{int(time.time())}"
    job = AgentJob(job_id=job_id, prompt=prompt, workspace=workspace, channel=channel, email_to=email_to)
    active_jobs[job_id] = job
    asyncio.create_task(job.execute())
    return job_id

def cancel_agent_task(job_id: str) -> tuple[bool, str]:
    job = active_jobs.get(job_id)
    if not job:
        return False, f"Job '{job_id}' not found or already finished."
    if job.process and job.process.returncode is None:
        try:
            job.process.kill()
            job.status = "CANCELLED"
            active_jobs.pop(job_id, None)
            return True, f"Cancelled job {job_id}."
        except Exception as e:
            return False, f"Failed to cancel job: {str(e)}"
    return False, "Job process not running."

# ----------------- MULTI-TURN AGENT THREAD SESSIONS -----------------
class MultiTurnAgentSession:
    def __init__(self, thread_id: int, thread: discord.Thread, workspace: str):
        self.thread_id = thread_id
        self.thread = thread
        self.workspace = workspace if (workspace and os.path.isdir(workspace)) else DEFAULT_WORKSPACE
        self.turns_count = 0
        self.is_busy = False

    async def run_turn(self, prompt: str):
        if self.is_busy:
            await self.thread.send("⏳ Agent is still working on the previous prompt. Please wait...")
            return

        self.is_busy = True
        self.turns_count += 1
        
        status_msg = await self.thread.send(f"🤖 **Turn {self.turns_count}:** Processing request...")

        # If turn > 1, use -c (--continue) to maintain conversation history
        cmd = [AGY_EXE]
        if self.turns_count > 1:
            cmd.extend(["-c", "-p", prompt, "--dangerously-skip-permissions"])
        else:
            cmd.extend(["-p", prompt, "--dangerously-skip-permissions"])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self.workspace
            )

            full_output = []
            last_edit = time.time()

            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    full_output.append(decoded)

                if time.time() - last_edit > 10:
                    last_edit = time.time()
                    snippet = "\n".join(full_output[-3:])
                    try:
                        await status_msg.edit(content=f"🤖 **Turn {self.turns_count} In Progress:**\n```text\n{snippet[-500:]}\n```")
                    except Exception:
                        pass

            await proc.wait()
            res_text = "\n".join(full_output)
            
            # Post final turn response
            if len(res_text) <= 1800:
                await self.thread.send(f"✅ **Turn {self.turns_count} Completed:**\n```text\n{res_text or '(No output)'}\n```")
            else:
                chunk = res_text[-1800:]
                await self.thread.send(f"✅ **Turn {self.turns_count} Completed:**\n```text\n...{chunk}\n```")
        except Exception as e:
            await self.thread.send(f"❌ Error during turn: {str(e)}")
        finally:
            self.is_busy = False

class MultiTurnManager:
    def __init__(self):
        self.sessions: Dict[int, MultiTurnAgentSession] = {}

    def get_session(self, thread_id: int) -> Optional[MultiTurnAgentSession]:
        return self.sessions.get(thread_id)

    def create_session(self, thread_id: int, thread: discord.Thread, workspace: str) -> MultiTurnAgentSession:
        session = MultiTurnAgentSession(thread_id=thread_id, thread=thread, workspace=workspace)
        self.sessions[thread_id] = session
        return session

    def close_session(self, thread_id: int) -> bool:
        return self.sessions.pop(thread_id, None) is not None

multi_turn_manager = MultiTurnManager()
