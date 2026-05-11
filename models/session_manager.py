from common.expired_dict import ExpiredDict
from common.log import logger
from config import conf


class Session(object):
    def __init__(self, session_id, system_prompt=None):
        self.session_id = session_id
        self.messages = []
        if system_prompt is None:
            self.system_prompt = conf().get("character_desc", "")
        else:
            self.system_prompt = system_prompt

    # 重置会话
    def reset(self):
        system_item = {"role": "system", "content": self.system_prompt}
        self.messages = [system_item]

    def set_system_prompt(self, system_prompt):
        self.system_prompt = system_prompt
        self.reset()

    def add_query(self, query):
        user_item = {"role": "user", "content": query}
        self.messages.append(user_item)

    def add_reply(self, reply):
        assistant_item = {"role": "assistant", "content": reply}
        self.messages.append(assistant_item)

    def discard_exceeding(self, max_tokens=None, cur_tokens=None):
        raise NotImplementedError

    def calc_tokens(self):
        raise NotImplementedError


class SessionManager(object):
    def __init__(self, sessioncls, **session_args):
        if conf().get("expires_in_seconds"):
            sessions = ExpiredDict(conf().get("expires_in_seconds"))
        else:
            sessions = dict()
        self.sessions = sessions
        self.sessioncls = sessioncls
        self.session_args = session_args
        self._store = None  # lazy ConversationStore ref; None = not yet tried

    # ------------------------------------------------------------------
    # Persistence helpers (normal mode — agent mode has its own path)
    # ------------------------------------------------------------------

    def _get_store(self):
        """Lazy-load the shared ConversationStore for normal-mode persistence."""
        if self._store is None:
            if conf().get("conversation_persistence", True):
                try:
                    from agent.memory import get_conversation_store
                    self._store = get_conversation_store()
                except Exception as e:
                    logger.warning(f"[SessionManager] ConversationStore init failed: {e}")
                    self._store = False  # sentinel — don't retry
            else:
                self._store = False
        return self._store if self._store and self._store is not False else None

    @staticmethod
    def _extract_text(content) -> str:
        """Convert stored JSON content (string or block list) to plain text."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            return "\n".join(p for p in parts if p).strip()
        return str(content)

    def _restore_session(self, session: Session):
        """Restore recent conversation history from the shared SQLite store."""
        store = self._get_store()
        if not store:
            return
        try:
            saved = store.load_messages(session.session_id, max_turns=15)
            if not saved:
                return
            for msg in saved:
                role = msg.get("role")
                if role not in ("user", "assistant"):
                    continue
                text = self._extract_text(msg.get("content", ""))
                if not text:
                    continue
                session.messages.append({"role": role, "content": text})
            logger.debug(
                f"[SessionManager] Restored {len(saved)} messages for "
                f"session={session.session_id}"
            )
        except Exception as e:
            logger.warning(
                f"[SessionManager] Failed to restore session "
                f"{session.session_id}: {e}"
            )

    def _persist_message(self, session_id: str, role: str, content: str):
        """Append a single message to the persistent store."""
        store = self._get_store()
        if not store:
            return
        try:
            store.append_messages(session_id, [{"role": role, "content": content}])
        except Exception as e:
            logger.warning(f"[SessionManager] Failed to persist message: {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_session(self, session_id, system_prompt=None):
        """
        如果session_id不在sessions中，创建一个新的session并添加到sessions中
        如果system_prompt不会空，会更新session的system_prompt并重置session
        """
        if session_id is None:
            return self.sessioncls(session_id, system_prompt, **self.session_args)

        if session_id not in self.sessions:
            session = self.sessioncls(session_id, system_prompt, **self.session_args)
            self.sessions[session_id] = session
            # Restore persisted conversation history (normal-mode persistence)
            self._restore_session(session)
        elif system_prompt is not None:  # 如果有新的system_prompt，更新并重置session
            self.sessions[session_id].set_system_prompt(system_prompt)
        session = self.sessions[session_id]
        return session

    def session_query(self, query, session_id):
        session = self.build_session(session_id)
        session.add_query(query)
        self._persist_message(session_id, "user", query)
        try:
            max_tokens = conf().get("conversation_max_tokens", 1000)
            total_tokens = session.discard_exceeding(max_tokens, None)
            logger.debug("prompt tokens used={}".format(total_tokens))
        except Exception as e:
            logger.warning("Exception when counting tokens precisely for prompt: {}".format(str(e)))
        return session

    def session_reply(self, reply, session_id, total_tokens=None):
        session = self.build_session(session_id)
        session.add_reply(reply)
        self._persist_message(session_id, "assistant", reply)
        try:
            max_tokens = conf().get("conversation_max_tokens", 1000)
            tokens_cnt = session.discard_exceeding(max_tokens, total_tokens)
            logger.debug("raw total_tokens={}, savesession tokens={}".format(total_tokens, tokens_cnt))
        except Exception as e:
            logger.warning("Exception when counting tokens precisely for session: {}".format(str(e)))
        return session

    def clear_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def clear_all_session(self):
        self.sessions.clear()
