# Multifunctional Telegram Bot

This repository contains a Python script that implements a multifunctional
Telegram bot.  The bot acts as a thin client around several free APIs
published on Cloudflare Workers.  It supports file downloads from
Terabox, video downloads from various social platforms, and chat
interfaces for both LLaMA 3.1 and GPT‑3.5 style models.  An
administrative interface allows selected Telegram IDs to view usage
statistics and broadcast messages.

## Features

* **Welcome and help commands** – The `/start` command greets users and
  displays an inline keyboard with quick‑access buttons.  The
  `/help` command lists all available commands.
* **Terabox downloader** – Users provide a Terabox share link and the
  bot returns a direct download link using the public Terabox API.
* **Social media downloader** – Downloads videos from YouTube,
  Instagram, TikTok or Facebook via the `nodejssocialdownloder` API.
* **LLaMA chat** – A lightweight chat interface to the uncensored
  *LLaMA 3.1 – 8B* model via the RevangeAPI worker.  In response to a
  simple query (`prompt=Hello`), the API returns a friendly greeting
  like `{"reply":"What's good bro"}`【568315267954781†screenshot】.
* **GPT‑3.5 chat** – Connects to the BJ Devs GPT‑3.5 endpoint.  Example
  output from `https://gpt-3-5.apis-bj-devs.workers.dev/?prompt=Hello`
  demonstrates that the service responds with structured JSON
  containing the assistant’s reply【450519771331906†screenshot】.
* **Usage quota** – A daily free‑tier limit (default 20 requests) is
  enforced per user.  Administrators can reset or raise quotas.
* **Admin tools** – Administrators can run `/stats` to view per‑user
  usage and `/broadcast <message>` to push announcements to all known
  users.

## Prerequisites

* Python 3.9 or newer.
* A Telegram bot token obtained from [@BotFather](https://core.telegram.org/bots#3-how-do-i-create-a-bot).
* (Optional) A VPS or a Koyeb account for deployment.

The bot relies on the [`python‑telegram‑bot` library](https://pypi.org/project/python-telegram-bot/).
According to its package description, this library provides a **pure
Python, asynchronous interface for the Telegram Bot API** and is
compatible with Python 3.9+【6391338732703†screenshot】.

## Installation

1.  Clone this repository or copy the `telegram_bot` directory onto
    your system.
2.  Create a virtual environment and install dependencies:

    ```bash
    cd telegram_bot
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  Set environment variables.  At minimum you must export the
    Telegram token obtained from BotFather.  You can also configure a
    comma separated list of administrator user IDs and the free‑tier
    limit:

    ```bash
    export TELEGRAM_BOT_TOKEN=123456:ABCDEF
    export ADMIN_IDS=987654321,123123123
    export FREE_TIER_LIMIT=20
    ```

## Running Locally

After installation and configuration, start the bot with:

```bash
python bot.py
```

The bot will poll the Telegram servers for updates.  Send `/start` to
your bot in Telegram to see the welcome message and test the features.

## Deployment on Koyeb

Koyeb is a serverless platform that can run containerized workloads
across their global edge network.  To deploy this bot on Koyeb:

1.  Commit your code to a Git repository or upload it to Koyeb.  Your
    repository should contain at least `bot.py`, `requirements.txt`
    and a `Procfile` with the following line:

    ```
    web: python bot.py
    ```

2.  On the Koyeb dashboard create a new **Service** and choose the
    **Git Repository** option.  Point it at your repository.
3.  Under **Build & Run**, specify the build command as:

    ```
    pip install -r requirements.txt
    ```

    and the run command as:

    ```
    python bot.py
    ```

4.  Define the environment variables (see above) in the **Secrets**
    section.
5.  Deploy the service.  Koyeb will spin up a container and your bot
    will start automatically.

## How it Works

The bot uses asynchronous HTTP requests to interact with the external
APIs.  When a user issues a command (e.g., `/terabox`), the bot
constructs the appropriate API URL and makes a request.  Responses
from the chat APIs include a `reply` field containing the generated
text, which the bot extracts and forwards to the user.  For
downloader APIs, the bot returns either the extracted download URL or
the raw JSON response.  A `UsageTracker` class counts how many times
each user invokes an API per day; if the free tier limit is reached
the bot politely declines further requests until the next day.

## Limitations and Future Ideas

* The sample does not persist usage counters across restarts; to add
  persistence you could store the data in a database or a simple
  file.
* Upgrade handling and payments are out of scope.  The Telegram bot
  platform supports payments via supported providers
  (e.g., Stripe, QiWi and Google Pay)【76074559833637†screenshot】, but this demo does
  not implement billing logic.
* The inline keyboard resets after a button press and does not
  remember the selected API.  A stateful conversation handler could
  improve the UX.

## License

This project is released under the MIT License.  Feel free to modify
and adapt it for your own use.