"""36-hour Monster AI curriculum — learn from GPT and the broader AI ecosystem."""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_DURATION_HOURS = 36


@dataclass
class CurriculumTopic:
    id: str
    phase: str
    query: str
    query_zh: str
    focus: str
    track: str = "ai"  # ai | lang | cyber


@dataclass
class CurriculumPhase:
    id: str
    title: str
    hours: str
    topics: list[CurriculumTopic] = field(default_factory=list)


def build_36h_curriculum() -> list[CurriculumPhase]:
    """GPT + major AI systems + training — paced for ~36 hours."""
    raw: list[tuple[str, str, str, list[tuple[str, str, str]]]] = [
        (
            "phase1",
            "AI 基礎與 GPT 架構 (0–6h)",
            "0-6",
            [
                ("transformer", "Transformer architecture attention mechanism", "Transformer 注意力機制與架構"),
                ("gpt-history", "OpenAI GPT model history GPT-1 GPT-2 GPT-3 GPT-4", "OpenAI GPT 發展史 GPT-4"),
                ("gpt-training", "GPT pretraining fine-tuning RLHF pipeline", "GPT 預訓練 微調 RLHF 流程"),
                ("llm-basics", "large language model tokenization context window", "大型語言模型 token 與上下文"),
                ("embedding", "text embeddings vector databases semantic search", "文字嵌入 向量資料庫 語意搜尋"),
                ("prompt-eng", "prompt engineering chain of thought few-shot", "提示工程 思維鏈 少樣本學習"),
                ("openai-api", "OpenAI API chat completions best practices 2024", "OpenAI API 聊天補全最佳實踐"),
                ("chatgpt", "ChatGPT capabilities limitations system prompts", "ChatGPT 能力 限制 系統提示"),
                ("chinese-llm", "Chinese LLM Breeze Taiwan LLM 中文大模型", "中文大語言模型 Breeze 台灣 LLM"),
                ("ollama", "Ollama local LLM deployment llama3", "Ollama 本地部署 LLM"),
                ("quantization", "LLM quantization GGUF 4bit 8bit inference", "LLM 量化 GGUF 推理加速"),
                ("gpu-inference", "GPU VRAM LLM inference optimization", "GPU 顯存 LLM 推理優化"),
            ],
        ),
        (
            "phase2",
            "主流 AI 模型生態 (6–12h)",
            "6-12",
            [
                ("claude", "Anthropic Claude AI constitutional AI safety", "Anthropic Claude 憲法 AI 安全"),
                ("gemini", "Google Gemini multimodal AI model", "Google Gemini 多模態模型"),
                ("llama", "Meta Llama 3 open source LLM", "Meta Llama 3 開源大模型"),
                ("mistral", "Mistral AI Mixtral MoE models", "Mistral Mixtral 混合專家模型"),
                ("qwen", "Alibaba Qwen LLM Chinese English", "通義千問 Qwen 中英模型"),
                ("deepseek", "DeepSeek LLM reasoning coding", "DeepSeek 推理與程式模型"),
                ("grok", "xAI Grok model real-time knowledge", "xAI Grok 即時知識模型"),
                ("copilot", "Microsoft Copilot GitHub Copilot architecture", "Microsoft Copilot 架構"),
                ("perplexity", "Perplexity AI search RAG architecture", "Perplexity 搜尋增強 RAG"),
                ("midjourney", "Midjourney diffusion image AI", "Midjourney 擴散模型圖像 AI"),
                ("stable-diffusion", "Stable Diffusion SDXL ComfyUI workflow", "Stable Diffusion SDXL ComfyUI"),
                ("whisper-tts", "OpenAI Whisper speech TTS Piper XTTS", "Whisper 語音辨識 TTS 合成"),
            ],
        ),
        (
            "phase3",
            "訓練與對齊技術 (12–18h)",
            "12-18",
            [
                ("finetune", "LLM fine-tuning supervised learning datasets", "LLM 監督式微調 資料集"),
                ("lora", "LoRA QLoRA parameter efficient fine tuning", "LoRA QLoRA 高效微調"),
                ("rlhf", "RLHF reinforcement learning human feedback PPO", "RLHF 人類回饋強化學習"),
                ("dpo", "DPO direct preference optimization alignment", "DPO 直接偏好優化 對齊"),
                ("distillation", "knowledge distillation teacher student LLM", "知識蒸餾 師生模型"),
                ("synthetic-data", "synthetic data generation for LLM training", "合成資料 LLM 訓練"),
                ("eval-benchmark", "MMLU HELM LLM evaluation benchmarks", "LLM 評測基準 MMLU"),
                ("hallucination", "LLM hallucination mitigation RAG grounding", "幻覺問題 RAG 接地緩解"),
                ("safety", "AI safety alignment red teaming", "AI 安全 對齊 紅隊測試"),
                ("bias-fairness", "AI bias fairness responsible AI", "AI 偏見 公平 負責任 AI"),
                ("opensource", "Hugging Face transformers model hub", "Hugging Face 開源模型生態"),
                ("peft", "PEFT adapters fine-tuning transformers", "PEFT 適配器微調"),
            ],
        ),
        (
            "phase4",
            "Agent 與應用架構 (18–24h)",
            "18-24",
            [
                ("rag", "retrieval augmented generation RAG pipeline", "RAG 檢索增強生成 管線"),
                ("agents", "AI agents ReAct tool use planning", "AI Agent ReAct 工具使用"),
                ("mcp", "Model Context Protocol MCP tools", "MCP 模型上下文協議"),
                ("function-calling", "LLM function calling tool schemas JSON", "LLM 函數呼叫 工具 schema"),
                ("memory", "AI long-term memory conversation state", "AI 長期記憶 對話狀態"),
                ("multi-agent", "multi-agent systems orchestration", "多 Agent 協作編排"),
                ("discord-bot", "Discord bot slash commands discord.py", "Discord 機器人 斜線指令"),
                ("fastapi-llm", "FastAPI LLM backend architecture", "FastAPI LLM 後端架構"),
                ("websocket-chat", "WebSocket streaming chat LLM", "WebSocket 串流聊天"),
                ("self-heal", "autonomous self-healing software watchdog", "自主修復 看門狗系統"),
                ("reflect-loop", "LLM reflect loop quality retry refinement", "Reflect 品質重試迴路"),
                ("preference-learn", "preference learning from user feedback AI", "用戶回饋偏好學習"),
            ],
        ),
        (
            "phase5",
            "多模態與生成 (24–30h)",
            "24-30",
            [
                ("vision-llm", "vision language models LLaVA GPT-4V", "視覺語言模型 VLM"),
                ("image-quality", "AI image quality scoring aesthetic CLIP", "圖像品質 CLIP 美學評分"),
                ("controlnet", "ControlNet img2img inpainting", "ControlNet 圖生圖 修補"),
                ("lora-image", "LoRA training Stable Diffusion character", "LoRA 訓練 角色 風格"),
                ("animatediff", "AnimateDiff video generation ComfyUI", "AnimateDiff 影片生成"),
                ("tts-piper", "Piper TTS local voice synthesis", "Piper 本地語音合成"),
                ("voice-clone", "XTTS voice cloning ethics", "XTTS 聲音克隆 倫理"),
                ("music-ai", "AI music generation Suno Udio", "AI 音樂生成"),
                ("code-llm", "code LLM Codex StarCoder programming", "程式碼大模型 Codex"),
                ("cybersec-ai", "AI cybersecurity threat detection", "AI 網路安全 威脅偵測"),
                ("edge-ai", "edge AI on-device inference mobile", "邊緣 AI 裝置端推理"),
                ("quantum-ai", "quantum computing AI intersection", "量子計算與 AI"),
            ],
        ),
        (
            "phase6",
            "Monster AI 自我進化 (30–36h)",
            "30-36",
            [
                ("monster-arch", "autonomous AI assistant local-first architecture", "本地優先自主 AI 架構"),
                ("monster-learn", "self-learning AI feedback loop evolution", "自我學習 AI 進化迴路"),
                ("monster-guard", "Discord moderation bot AI scam detection", "Discord 防詐 AI 審核"),
                ("callguard", "phone scam detection CallGuard Android", "電話詐騙偵測 CallGuard"),
                ("crimeguard", "CrimeGuard network lock privacy HK", "CrimeGuard 網絡安全鎖"),
                ("persona-grok", "AI persona uncensored local Grok style", "本地 Grok 風格人格"),
                ("zh-tw-ai", "Traditional Chinese AI localization zh-TW", "繁體中文 AI 在地化"),
                ("training-export", "export LLM training dataset JSONL alpaca", "匯出 LLM 訓練 JSONL"),
                ("ollama-finetune", "Ollama modelfile custom system prompt", "Ollama Modelfile 自訂模型"),
                ("future-agi", "AGI ASI timeline AI future 2026", "AGI 發展趨勢 2026"),
                ("ai-ethics-local", "local AI user privacy data sovereignty", "本地 AI 隱私 資料主權"),
                ("monster-24-7", "24/7 autonomous AI daemon self-improve", "24/7 自主 AI 持續改進"),
            ],
        ),
    ]

    phases: list[CurriculumPhase] = []
    for pid, title, hours, topics in raw:
        phase = CurriculumPhase(id=pid, title=title, hours=hours)
        for tid, q_en, q_zh in topics:
            phase.topics.append(
                CurriculumTopic(
                    id=tid,
                    phase=pid,
                    query=f"{q_en} {q_zh}",
                    query_zh=q_zh,
                    focus=q_en,
                )
            )
        phases.append(phase)
    return phases


def _phase_from_raw(
    pid: str,
    title: str,
    hours: str,
    topics: list[tuple[str, str, str]],
    *,
    track: str = "ai",
) -> CurriculumPhase:
    phase = CurriculumPhase(id=pid, title=title, hours=hours)
    for tid, q_en, q_zh in topics:
        phase.topics.append(
            CurriculumTopic(
                id=tid,
                phase=pid,
                query=f"{q_en} {q_zh}",
                query_zh=q_zh,
                focus=q_en,
                track=track,
            )
        )
    return phase


def build_languages_curriculum() -> CurriculumPhase:
    """World languages + programming languages + i18n — network learning."""
    topics = [
        ("lang-en", "English grammar communication global lingua franca", "英語語法與全球溝通"),
        ("lang-zh-cn", "Simplified Chinese Mandarin language culture", "簡體中文普通話語言文化"),
        ("lang-zh-tw", "Traditional Chinese Taiwan Hong Kong usage", "繁體中文台灣香港用語"),
        ("lang-ja", "Japanese language hiragana katakana keigo", "日語平假名片假名敬語"),
        ("lang-ko", "Korean language hangul honorifics", "韓語諺文敬語體系"),
        ("lang-es", "Spanish language Latin America Spain", "西班牙語拉美與歐洲"),
        ("lang-fr", "French language grammar pronunciation", "法語語法發音"),
        ("lang-de", "German language grammar cases", "德語格變化語法"),
        ("lang-ar", "Arabic language Modern Standard Arabic", "阿拉伯語現代標準語"),
        ("lang-hi", "Hindi language Devanagari script India", "印地語天城文印度"),
        ("lang-ru", "Russian language Cyrillic grammar", "俄語西里爾字母語法"),
        ("lang-pt", "Portuguese Brazil Portugal language", "葡萄牙語巴西歐洲"),
        ("lang-it", "Italian language grammar culture", "義大利語語法文化"),
        ("lang-nl", "Dutch language Netherlands Flemish", "荷蘭語佛蘭德語"),
        ("lang-pl", "Polish language Slavic grammar", "波蘭語斯拉夫語法"),
        ("lang-tr", "Turkish language agglutination", "土耳其語黏著語"),
        ("lang-vi", "Vietnamese language tones grammar", "越南語聲調語法"),
        ("lang-th", "Thai language script tones", "泰語文字聲調"),
        ("lang-id", "Indonesian Malay language", "印尼馬來語"),
        ("lang-he", "Hebrew language modern Israeli", "現代希伯來語"),
        ("lang-sv", "Swedish Nordic languages", "瑞典語北歐語言"),
        ("lang-sw", "Swahili East Africa lingua franca", "斯瓦希里語東非"),
        ("lang-fa", "Persian Farsi language", "波斯語法爾斯語"),
        ("lang-uk", "Ukrainian language Cyrillic", "烏克蘭語"),
        ("lang-bn", "Bengali language Bangladesh India", "孟加拉語"),
        ("lang-ta", "Tamil language South India Sri Lanka", "泰米爾語"),
        ("lang-ms", "Malay language Malaysia Singapore", "馬來語"),
        ("lang-el", "Greek language ancient modern", "希臘語古今"),
        ("lang-cs", "Czech language Slavic", "捷克語"),
        ("lang-ro", "Romanian language Latin roots", "羅馬尼亞語"),
        ("lang-hu", "Hungarian language Finno-Ugric", "匈牙利語"),
        ("lang-fi", "Finnish language Uralic", "芬蘭語"),
        ("lang-no", "Norwegian Scandinavian languages", "挪威語斯堪地那維亞"),
        ("lang-da", "Danish language Scandinavian", "丹麥語"),
        ("lang-ca", "Catalan language Spain", "加泰隆尼亞語"),
        ("lang-eu", "Basque language isolate", "巴斯克語"),
        ("lang-gl", "Galician language Spain", "加里西亞語"),
        ("lang-ga", "Irish Gaelic Celtic language", "愛爾蘭蓋爾語"),
        ("lang-cy", "Welsh Celtic language", "威爾斯語"),
        ("lang-mt", "Maltese language Semitic Latin", "馬爾他語"),
        ("lang-si", "Sinhala Sri Lanka language", "僧伽羅語"),
        ("lang-ne", "Nepali language Himalaya", "尼泊爾語"),
        ("lang-my", "Burmese Myanmar language", "緬甸語"),
        ("lang-km", "Khmer Cambodian language", "高棉語"),
        ("lang-lo", "Lao language tones script", "寮語"),
        ("lang-mn", "Mongolian language script", "蒙古語"),
        ("lang-ur", "Urdu language Pakistan Nastaliq", "烏爾都語"),
        ("lang-pa", "Punjabi language Gurmukhi Shahmukhi", "旁遮普語"),
        ("lang-gu", "Gujarati language India", "古吉拉特語"),
        ("lang-te", "Telugu language South India", "泰盧固語"),
        ("lang-mr", "Marathi language India", "馬拉地語"),
        ("lang-i18n", "software internationalization localization i18n l10n", "軟體國際化在地化 i18n"),
        ("lang-unicode", "Unicode UTF-8 multilingual text encoding", "Unicode UTF-8 多語言編碼"),
        ("lang-translate", "machine translation NMT multilingual AI", "神經機器翻譯多語言 AI"),
        ("lang-python", "Python programming language best practices", "Python 程式語言最佳實踐"),
        ("lang-rust", "Rust programming memory safety systems", "Rust 程式語言記憶體安全"),
        ("lang-go", "Go Golang concurrency backend", "Go 語言並發後端"),
        ("lang-cpp", "C++ systems programming performance", "C++ 系統程式效能"),
        ("lang-ts", "TypeScript JavaScript type safety web", "TypeScript 網頁型別安全"),
        ("lang-kotlin", "Kotlin Android JVM language", "Kotlin Android 開發"),
        ("lang-swift", "Swift iOS Apple development", "Swift iOS 開發"),
        ("lang-java", "Java enterprise JVM ecosystem", "Java 企業 JVM 生態"),
        ("lang-sql", "SQL database query optimization", "SQL 資料庫查詢優化"),
        ("lang-bash", "Bash shell scripting Linux automation", "Bash Shell 自動化"),
        ("lang-powershell", "PowerShell Windows automation security", "PowerShell 自動化安全"),
    ]
    return _phase_from_raw(
        "phase7",
        "全球語言與程式語言 (36–54h)",
        "36-54",
        topics,
        track="lang",
    )


def build_cybersec_curriculum() -> CurriculumPhase:
    """Defensive cybersecurity and countermeasure techniques — network learning."""
    topics = [
        ("cyber-defense", "cybersecurity defense in depth strategy", "資安防禦縱深策略"),
        ("cyber-firewall", "firewall network security rules iptables", "防火牆網路安全規則"),
        ("cyber-ids-ips", "IDS IPS intrusion detection prevention", "入侵偵測與防禦系統"),
        ("cyber-siem", "SIEM security monitoring Splunk ELK", "SIEM 安全監控日誌分析"),
        ("cyber-zero-trust", "zero trust architecture network security", "零信任架構"),
        ("cyber-ddos", "DDoS mitigation CDN rate limiting", "DDoS 攻擊緩解與限速"),
        ("cyber-waf", "web application firewall OWASP rules", "WAF 網頁應用防火牆"),
        ("cyber-owasp", "OWASP Top 10 web vulnerabilities defense", "OWASP Top 10 漏洞防禦"),
        ("cyber-sql-def", "SQL injection prevention parameterized queries", "SQL 注入防禦參數化查詢"),
        ("cyber-xss-def", "XSS cross-site scripting prevention CSP", "XSS 跨站腳本防禦 CSP"),
        ("cyber-csrf", "CSRF token defense same-site cookies", "CSRF 跨站請求偽造防禦"),
        ("cyber-auth", "authentication MFA OAuth2 JWT security", "身份驗證 MFA OAuth2 安全"),
        ("cyber-pki", "TLS SSL PKI certificate management", "TLS SSL 憑證管理 PKI"),
        ("cyber-encrypt", "encryption AES RSA at rest in transit", "加密靜態與傳輸中資料"),
        ("cyber-secrets", "secrets management vault rotation", "密鑰管理輪換"),
        ("cyber-hardening", "server hardening CIS benchmarks Linux Windows", "伺服器強化 CIS 基準"),
        ("cyber-edr", "EDR endpoint detection response", "端點偵測與回應 EDR"),
        ("cyber-malware-def", "malware defense antivirus sandbox analysis", "惡意軟體防禦沙箱分析"),
        ("cyber-ransomware", "ransomware prevention backup isolation", "勒索軟體防禦備份隔離"),
        ("cyber-phishing", "phishing detection email security DMARC", "釣魚攻擊偵測郵件安全"),
        ("cyber-scam", "phone scam fraud detection AI countermeasures", "電話詐騙 AI 偵測反制"),
        ("cyber-social", "social engineering defense awareness training", "社交工程防禦意識訓練"),
        ("cyber-vpn-sec", "VPN security WireGuard IPsec best practices", "VPN 安全 WireGuard"),
        ("cyber-network-seg", "network segmentation microsegmentation", "網路分段微分段"),
        ("cyber-blue-team", "blue team SOC incident response playbook", "藍隊 SOC 事件應變"),
        ("cyber-forensics", "digital forensics evidence chain custody", "數位鑑識證據鏈"),
        ("cyber-log-analysis", "security log analysis anomaly detection", "安全日誌異常偵測"),
        ("cyber-api-sec", "API security rate limit OAuth abuse", "API 安全速率限制"),
        ("cyber-container", "container security Docker Kubernetes hardening", "容器安全 K8s 強化"),
        ("cyber-cloud-sec", "cloud security AWS Azure IAM least privilege", "雲端安全最小權限 IAM"),
        ("cyber-mobile", "mobile app security Android iOS hardening", "行動應用安全強化"),
        ("cyber-iot", "IoT security device firmware update", "物聯網設備安全韌體"),
        ("cyber-supply-chain", "software supply chain SBOM dependency audit", "軟體供應鏈 SBOM 審計"),
        ("cyber-threat-intel", "threat intelligence IOC MITRE ATT&CK defense", "威脅情報 MITRE ATT&CK 防禦"),
        ("cyber-honeypot", "honeypot deception technology attacker trap", "蜜罐誘捕攻擊者技術"),
        ("cyber-red-blue", "red team blue team purple team exercises", "紅藍軍對抗演練"),
        ("cyber-gdpr", "privacy GDPR data protection compliance", "GDPR 隱私資料保護"),
        ("cyber-hk-law", "Hong Kong cybersecurity law PCPD data privacy", "香港網路安全與私隱條例"),
        ("cyber-monsterlock", "hardware binding anti-tamper software protection", "硬體綁定防篡改保護"),
        ("cyber-crimeguard", "network lock localhost crime detection AI", "網絡鎖定犯罪偵測 AI"),
        ("cyber-callguard", "call guard scam phone fraud Android defense", "CallGuard 電話詐騙防禦"),
        ("cyber-ai-defense", "AI adversarial attack defense model security", "AI 對抗攻擊模型安全防禦"),
        ("cyber-prompt-inject", "LLM prompt injection defense guardrails", "LLM 提示注入防禦"),
        ("cyber-bot-defense", "Discord bot moderation anti-spam anti-scam", "Discord 機器人防詐騙"),
        ("cyber-automation", "security automation SOAR playbook orchestration", "安全自動化 SOAR 編排"),
        ("cyber-resilience", "cyber resilience business continuity disaster recovery", "網路韌性災難復原"),
    ]
    return _phase_from_raw(
        "phase8",
        "資安反制與防禦技術 (54–72h)",
        "54-72",
        topics,
        track="cyber",
    )


def build_curriculum(mode: str = "base") -> list[CurriculumPhase]:
    """base=AI 36h | extended=AI+語言+資安 | languages | cybersec | full."""
    base = build_36h_curriculum()
    lang = build_languages_curriculum()
    cyber = build_cybersec_curriculum()
    if mode in ("base", "ai"):
        return base
    if mode == "languages":
        return [lang]
    if mode in ("cyber", "cybersec"):
        return [cyber]
    if mode == "after_ai":
        return [lang, cyber]
    # extended | full
    return base + [lang, cyber]


def flat_topics(phases: list[CurriculumPhase] | None = None, *, mode: str = "base") -> list[CurriculumTopic]:
    phases = phases or build_curriculum(mode)
    out: list[CurriculumTopic] = []
    for phase in phases:
        out.extend(phase.topics)
    return out


def topic_count(mode: str = "base") -> int:
    return len(flat_topics(mode=mode))


def default_hours_for_mode(mode: str) -> float:
    counts = {
        "base": 36.0,
        "ai": 36.0,
        "extended": 72.0,
        "full": 72.0,
        "languages": 24.0,
        "after_ai": 48.0,
        "cybersec": 24.0,
        "cyber": 24.0,
    }
    return counts.get(mode, 36.0)