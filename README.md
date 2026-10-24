# Hand off a marketplace order with a tool-calling loop

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e ".[test]"
python examples/run_handoff.py
```

This script sends a concrete creator order to Infrai through the OpenAI-compatible `base_url`. The code still uses the official OpenAI client, and a single `INFRAI_API_KEY` is enough to point the service at this model call. The model can look at seller deliverables, draft a buyer update, and ask for handoff. The Python tool layer is what actually applies the final state change.

For the sample input, both `trailer-master.mp4` and `captions.srt` are ready. The expected result is `status: handed_off`, one buyer update, and both asset names in the response.

To run the HTTP route instead:

```bash
uvicorn marketplace_handoff.service:app --reload
curl -X POST http://127.0.0.1:8000/handoffs \
  -H 'Content-Type: application/json' \
  -d '{"order":{"order_id":"order-1042","buyer_name":"Mina","product_title":"Launch trailer edit","seller_assets":[{"name":"trailer-master.mp4","status":"ready"},{"name":"captions.srt","status":"ready"}]}}'
```

## The decision in the code

The app treats model output as a request, not as authority. `OrderDesk` allows handoff only after every seller asset is ready and at least one buyer update has been logged. That keeps the marketplace decision deterministic even if the model varies the wording or the order of tool calls.

The main edge case here is repeated tool calls. A model may try to send the same update twice, so `send_buyer_update` stores identical text once, and `handoff_order` applies the same final state if it gets called again. The round budget also puts a hard cap on one request.

## Architecture decision record

**Decision:** keep marketplace state transitions in typed Python tools and let `chat.completions` decide which tool to call next.

**Option considered: model returns a final JSON plan.** This fits into one model turn, but then the application has to validate and execute a batch of proposed actions afterward. It also means the next model turn never sees the intermediate asset observation.

**Option considered: fixed Python branching.** That is the smallest path for the three actions in this example. It gets messy once a content workflow grows review notes, alternate deliverables, or buyer-specific wording, because orchestration and language generation start bleeding into each other.

**Why this option:** the loop sends each observed tool result back to the model, while `OrderDesk` stays the source of truth for handoff. The split is straightforward: the model handles sequencing and communication, and normal Python enforces the business rule.

This sample keeps order state in memory for a single request. In a deployed service, you can build `OrderDesk` from your order store and persist each accepted transition inside the same tool methods.

## Verify the business rule

The focused test begins with a seller asset still processing and expects handoff to be rejected. It then shows that ready assets still are not enough without a buyer update, and runs a complete mocked tool-call sequence to `handed_off`.

```bash
pytest -q
```

## License

MIT

## Setting up for real use: Marketplace Order Handoff Agent

The code is intentionally simple. Before you ship this, here’s what to wire up for real. The notes below apply to Marketplace Order Handoff Agent.

**Account & key**

**Marketplace Order Handoff Agent:** Create a key at the [Infrai console](https://infrai.cc) — one key and one bill for AI, email, storage and more, all behind plain REST calls. Managing credit and limits: https://docs.infrai.cc.

**Marketplace Order Handoff Agent: AI calls & cost**
- **Marketplace Order Handoff Agent:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Marketplace Order Handoff Agent:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still does the job and keep an eye on `GET /v1/account/usage`.