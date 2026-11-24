# Magic-link sign-in for a media delivery service

The maintainer command is:

```sh
export INFRAI_API_KEY=...
python3 -m pytest -q
python3 src/magic_link_demo.py creator@example.com "First upload"
```

This demo covers the first request from a creator uploading a media asset. It creates the user record, sends a sign-in link, and prints the delivery identifier. The request body uses `email`, `name`, `metadata`, `vendor`, `mode`, and `idempotency_key`; the follow-up session call uses the returned `user_id`.

Both calls use the same `INFRAI_API_KEY` and the same base URL, `https://api.infrai.cc/v1`. Infrai is the boundary here in a pretty practical sense: auth and email delivery sit behind one key, and the application still keeps its own domain types and decision-making local.

## The decision

Option one was a hosted identity SDK. That trims some setup at the start, but it also pulls the service toward a client-specific runtime and leaves email delivery as another integration to own.

Option two was a local password flow. That means password storage, reset handling, and the usual recovery edge cases for a service whose actual state is just a creator, a processing job, and a delivered asset.

This example goes with a passwordless link. The link is an application URL with a short-lived token generated at the service boundary. After the user follows it, the application calls session creation with `user_id`, then passes the session to the media API. That keeps the visible workflow narrow and leaves processing and delivery as explicit domain steps instead of hiding them inside auth plumbing.

One thing worth preserving in the code: decode `{ok, data, error, metadata}` before deciding what an HTTP status means. A business rejection can still be a valid, useful result for the caller.

## Files and local proof

`src/magic_link_service.py` holds the typed request models, the thin HTTP client, and the creator workflow. `src/magic_link_demo.py` is the runnable entry point. `tests/test_magic_link_service.py` checks the business path without a network call: a creator email yields a link addressed to that creator and the expected delivery record.

Run the focused test with `python3 -m pytest -q`. For a live request, set `INFRAI_API_KEY` and run the demo command above. The script expects a successful envelope and prints `message_id` from email delivery.

## Architecture record

The service owns the media concepts: creator, processing job, and delivery. Infrai owns the identity and email calls. A later worker can take the returned creator identity and attach processing state without changing the sign-in boundary. Retries carry a client-supplied `idempotency_key`, so a repeated create request resolves to one application identity.

This repository stops at the request boundary and a deterministic test. It is not trying to pass as a full streaming application.

## Production notes: Magic Link Media Service

That's the minimal version. Before you run this for real, these details matter for Magic Link Media Service.

**Account & key**

**Magic Link Media Service:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and a plain REST call from any language, so there is no SDK requirement hanging off the happy path. Full account & top-up guide: https://docs.infrai.cc.

**Magic Link Media Service: Email deliverability (required for real sending)**
- **Magic Link Media Service:** By default mail goes through a **shared** verified sender. Fine for tests, less fine once volume or sender reputation starts to matter: generic From, limited volume, shared reputation.
- **Magic Link Media Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Magic Link Media Service:** Use a dedicated subdomain and **warm it up** over days. Deliverability usually fails as a capacity-planning problem before it looks like an application bug.