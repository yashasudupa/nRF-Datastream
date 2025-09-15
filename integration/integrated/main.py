# main.py
import asyncio, time
from .json_writer import JSONLinesWriter
from .insole import run_insoles
from .ball import run_ball
from .metrics import detect_events, temporal_metrics

async def main():
    out_file = "Ball_Insole_Metrics.jsonl"
    writer = JSONLinesWriter(out_file)
    print("[INFO] Output:", out_file)

    # One stop event to rule them all
    stop_event = asyncio.Event()

    # Start both tasks and give them the SAME writer + stop_event
    insole_task = asyncio.create_task(run_insoles(writer, stop_event=stop_event))
    ball_task   = asyncio.create_task(run_ball(writer,    stop_event=stop_event))

    # Wait for a single ENTER then signal both tasks to stop
    print("Recording... press ENTER once to stop ball + insoles")
    await asyncio.to_thread(input)  # blocks a thread, not the event loop
    stop_event.set()

    # Wait; avoid ball hanging forever after stop
    try:
        ball_result = await asyncio.wait_for(ball_task, timeout=180.0)
    except asyncio.TimeoutError:
        print("[WARN] Ball task timed out; continuing.")
        ball_result = {}

    insoles_data = await insole_task

    # --- compute & append insole metrics (example for left) ---
    foot = "left"
    if foot in insoles_data:
        t  = insoles_data[foot]["t"]
        fb = insoles_data[foot]["forces_by_label"]
        events = detect_events(t, fb)
        tm     = temporal_metrics(t, events["HS"], events["TO"], events["stance"])

        # 1) Gait event + temporal summary
        writer.append({
            "timestamp": time.time(),
            "foot": foot,
            "gait_events": {
                "threshold_N": events["threshold"],
                "HS_idx": events["HS"],
                "TO_idx": events["TO"],
                "stance_idx": events["stance"],
                "swing_idx": events["swing"]
            },
            "temporal_metrics": {
                "CT_s": tm["CT"],
                "FT_s": tm["FT"],
                "stride_s": tm["stride"],
                "stride_freq_hz": tm["stride_freq"]
            }
        })

        # 2) COP path
        writer.append({
            "timestamp": time.time(),
            "foot": foot,
            "cop_path": events["COP"]
        })

    # 3) (Optional) append ball summary again near end if your run_ball returns it
    if isinstance(ball_result, dict) and ball_result.get("ball_summary"):
        writer.append({
            "timestamp": time.time(),
            "ball_summary": ball_result["ball_summary"]
        })

    # End marker
    writer.append({"event": "session_end", "t": int(time.time() * 1000)})
    print(f"[DONE] Saved JSONL: {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
