# Oblio exporter (python version)

In Romania, every limited responsibility company must store the bills they were issued for 5 years. However, [the website](https://www.oblio.eu/) my mom uses to handle billing (oblio) only keeps the bills received by her company for 2 months. Therefore mom, who essentially learned to use the computer in the last 10 years because it was a must for owning a company, needs her own resilient storage solution where she can back up all those invoices.

I wrote this to help my mom avoid the hassle of hard drives and monthly click-ops. Basically, the program authenticates to her account and for each of her companies, downloads a monthly export of all her bills for that month (in both .pdf and .xml formats required by our national fiscal administration agency) and saves those files with a descriptive name in backblaze. That amounts to 6 download processes every month, plus the renaming of the very cryptic original export names and the backblaze backup.

## Running the solution

Set your environment variables:

```bash
export OBLIO_EMAIL=
export OBLIO_PASSWORD=
export OBLIO_FIREFOX_PROFILE_PATH=
# format: year,month like "2024,12". Used to bypass manual month introduction
export BILLING_PERIOD=
export BACKBLAZE_S3_KEY_ID=
export BACKBLAZE_S3_APP_KEY=
export BACKBLAZE_BUCKET_NAME=
```

Then run:

```bash
python3 main.py
```
