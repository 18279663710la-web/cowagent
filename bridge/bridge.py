from models.bot_factory import create_bot
from bridge.context import Context
from bridge.reply import Reply
from common import const
from common.log import logger
from common.singleton import singleton
from config import conf
from translate.factory import create_translator
from voice.factory import create_voice


@singleton
class Bridge(object):
    def __init__(self):
        self.btype = {
            "chat": const.OPENAI,
            "voice_to_text": conf().get("voice_to_text", "openai"),
            "text_to_voice": conf().get("text_to_voice", "google"),
            "translate": conf().get("translate", "baidu"),
        }
        model_type = conf().get("model") or const.GPT_41_MINI
        if not isinstance(model_type, str):
            model_type = str(model_type)

        # Use shared resolution logic (single source of truth with AgentLLMModel)
        self.btype["chat"] = const.resolve_bot_type(
            model_type,
            configured_bot_type=conf().get("bot_type", ""),
            use_linkai=conf().get("use_linkai", False),
            linkai_api_key=conf().get("linkai_api_key", ""),
        )
        # Azure override
        if conf().get("use_azure_chatgpt", False):
            self.btype["chat"] = const.CHATGPTONAZURE
        # Legacy text-davinci-003 check
        if model_type in ["text-davinci-003"]:
            self.btype["chat"] = const.OPEN_AI
        # LinkAI overrides voice types too
        if conf().get("use_linkai") and conf().get("linkai_api_key"):
            if not conf().get("voice_to_text") or conf().get("voice_to_text") in ["openai"]:
                self.btype["voice_to_text"] = const.LINKAI
            if not conf().get("text_to_voice") or conf().get("text_to_voice") in ["openai", const.TTS_1, const.TTS_1_HD]:
                self.btype["text_to_voice"] = const.LINKAI

        self.bots = {}
        self.chat_bots = {}
        self._agent_bridge = None

    # 模型对应的接口
    def get_bot(self, typename):
        if self.bots.get(typename) is None:
            logger.info("create bot {} for {}".format(self.btype[typename], typename))
            if typename == "text_to_voice":
                self.bots[typename] = create_voice(self.btype[typename])
            elif typename == "voice_to_text":
                self.bots[typename] = create_voice(self.btype[typename])
            elif typename == "chat":
                self.bots[typename] = create_bot(self.btype[typename])
            elif typename == "translate":
                self.bots[typename] = create_translator(self.btype[typename])
        return self.bots[typename]

    def get_bot_type(self, typename):
        return self.btype[typename]

    def fetch_reply_content(self, query, context: Context) -> Reply:
        return self.get_bot("chat").reply(query, context)

    def fetch_voice_to_text(self, voiceFile) -> Reply:
        return self.get_bot("voice_to_text").voiceToText(voiceFile)

    def fetch_text_to_voice(self, text) -> Reply:
        return self.get_bot("text_to_voice").textToVoice(text)

    def fetch_translate(self, text, from_lang="", to_lang="en") -> Reply:
        return self.get_bot("translate").translate(text, from_lang, to_lang)

    def find_chat_bot(self, bot_type: str):
        if self.chat_bots.get(bot_type) is None:
            self.chat_bots[bot_type] = create_bot(bot_type)
        return self.chat_bots.get(bot_type)

    def reset_bot(self):
        """
        重置bot路由
        """
        self.__init__()

    def get_agent_bridge(self):
        """
        Get agent bridge for agent-based conversations
        """
        if self._agent_bridge is None:
            from bridge.agent_bridge import AgentBridge
            self._agent_bridge = AgentBridge(self)
            # Inject CharacterManager if character system is active
            try:
                from characters.registry import get_character_manager, get_proactive_service
                char_mgr = get_character_manager()
                if char_mgr:
                    self._agent_bridge.set_character_manager(char_mgr)
                proactive_svc = get_proactive_service()
                if proactive_svc:
                    self._agent_bridge.set_proactive_service(proactive_svc)
                    if char_mgr:
                        char_mgr.set_agent_bridge(self._agent_bridge)
                    proactive_svc.set_agent_bridge(self._agent_bridge)
            except Exception:
                pass
        return self._agent_bridge

    def fetch_agent_reply(self, query: str, context: Context = None,
                          on_event=None, clear_history: bool = False) -> Reply:
        """
        Use super agent to handle the query

        Args:
            query: User query
            context: Context object
            on_event: Event callback for streaming
            clear_history: Whether to clear conversation history

        Returns:
            Reply object
        """
        agent_bridge = self.get_agent_bridge()
        return agent_bridge.agent_reply(query, context, on_event, clear_history)
