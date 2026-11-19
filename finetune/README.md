# Fine-tuning data importers (GSMS-B)

```bash
python finetune/importers/gsmsb_qa.py        # -> finetune/data/gsmsb_qa_{train,test}.jsonl
python finetune/importers/gsmsb_mapping.py   # -> finetune/data/gsmsb_mapping_{train,test}.jsonl
python finetune/importers/verify.py          # independent re-check against the raw datasets
```

Needs only the Python standard library and internet access to huggingface.co (files are cached in `finetune/data/_cache`).
The system prompt is taken from `backend/app/rag/rag_pipeline.py` at run time, so it always matches the app.

Format: `{"messages":[system,user,assistant], "meta":{...}}` (chat format; train on the assistant turn only).

* **Train/test are split by section**, so no test section appears in training.
* `meta.needs_bnss_in_store=true` marks CrPC<->BNSS examples. BNSS is not ingested in the app yet; drop them (`--no-bnss`) until it is.
* English-only QA; mapping covers English, Hinglish and Hindi from hand-written templates (repetitive by design: cap them at ~20-30% of the mix).
