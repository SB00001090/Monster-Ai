module.exports = {
  apps: [
    {
      name: "monsterguard",
      script: "python",
      args: "-m monster_ai.modules.discord.standalone",
      cwd: "/opt/monster-ai",
      autorestart: true,
      max_restarts: 10,
      restart_delay: 10000,
      env: {
        MONSTER_AI_CONNECT_CONSENT: "1",
      },
    },
  ],
};