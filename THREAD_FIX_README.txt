PremiumEmoji hosting fix
=========================
Changed TeleBot worker threads to num_threads=1 to prevent
RuntimeError: can't start new thread on limited hosting.

Important: run only ONE instance of the bot at a time. If an old
PremiumEmoji.py process is still running, stop it before starting
the fixed version.
