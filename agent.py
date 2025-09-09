import logging 
import os
os.environ["LIVEKIT_DISABLE_INFERENCE"] = "1"  
import json
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext 
from livekit.plugins import (
    google,
    openai, 
    deepgram,
    cartesia,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from mcp_client import MCPServerSse
from mcp_client.agent_tools import MCPToolsIntegration
from prompts import SESSION_INSTRUCTIONS, AGENT_INSTRUCTIONS
from tools.tool_registry import ToolRegistry
from mem0 import AsyncMemoryClient

load_dotenv('.env')

class Assistant(Agent):
    def __init__(self, chat_ctx = None) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTIONS,
            stt=deepgram.STT(model="nova-3", language="multi"),
            llm=openai.realtime.RealtimeModel(temperature=0.8, voice="echo"),
            tools=ToolRegistry().get_active_tools(),
            tts=cartesia.TTS(model="sonic-2", voice="4f7f1324-1853-48a6-b294-4e78e8036a83"),
            vad=silero.VAD.load(),
            turn_detection=MultilingualModel(),
            chat_ctx=chat_ctx, 
        )

async def entrypoint(ctx: agents.JobContext):
    
    async def shutdown_hook(chat_ctx: ChatContext, mem0: AsyncMemoryClient, memory_str: str = ""):
        logging.info("Shutdown hook triggered, saving conversation to memory.")
        
        messages_formatted = [
            
        ]
        logging.info(f"Chat context messages: {chat_ctx.items}")
        
        for item in chat_ctx.items:
            content_str = ''.join(item.content) if isinstance(item.content, list) else str(item.content)
            
            if memory_str and memory_str in content_str:
                continue
                
            if item.role in ["user", "assistant"]:
                messages_formatted.append({
                    "role": item.role,
                    "content": content_str.strip()
                })
                
        logging.info(f"Formatted messages addded to memory: {messages_formatted}")
        await mem0.add(messages_formatted, user_id = "Yassin")
        logging.info("Conversation saved to memory successfully.")
    
    session = AgentSession()

    
    mem0 = AsyncMemoryClient()
    user_name = "Yassin"
    
    results = await mem0.get_all(user_id = user_name)
    initial_ctx = ChatContext()
    memory_str = ''
    
    if results:
        memories = [
            {
            "memory": result['memory'],
            "updated_at": result['updated_at']
            }     
            for result in results   
        ]
        memory_str = json.dumps(memories)
        logging.info(f"Memories found: {memory_str}")
        initial_ctx.add_message(
            role="assistant",
            content=f"The following is a list of memories from previous conversations with the user {user_name}: {memory_str}"
        )

    mcp_server = MCPServerSse(
        params={"url": os.environ.get("N8N_MCP_SERVER_URL")},
        cache_tools_list=True,
        name="SSE MCP Server"
    )

    agent = await MCPToolsIntegration.create_agent_with_tools(
        agent_class=Assistant, agent_kwargs={"chat_ctx": initial_ctx},
        mcp_servers=[mcp_server]
    )

    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(), 
        ),
    )
    await ctx.connect()

    await session.generate_reply(
        instructions=SESSION_INSTRUCTIONS
    )
    
    ctx.add_shutdown_callback(lambda: shutdown_hook(session._agent.chat_ctx, mem0, memory_str))

if __name__ == "__main__":
    # Simple WorkerOptions without invalid parameters
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )
