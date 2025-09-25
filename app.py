import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import dev_recorder
import software_checker

st.set_page_config(page_title="NeuroMuscleAI-MVP1", layout="centered")

st.title("NeuroMuscleAI-MVP1 — Dev Recorder Demo")

st.markdown("This is a minimal private scaffold demonstrating the dev recorder and environment checks.")

col1, col2 = st.columns(2)

with col1:
    if st.button("Start Recorder"):
        ok = dev_recorder.start()
        st.success("Recorder started" if ok else "Recorder already running")
    if st.button("Stop Recorder"):
        dev_recorder.stop()
        st.info("Recorder stopped")

    if st.button("Take Snapshot (once)"):
        dev_recorder.snapshot_env()
        dev_recorder.take_snapshot()
        st.success("Snapshot taken")

    cmd = st.text_input("Record command manually", value="")
    if st.button("Record Command") and cmd.strip():
        dev_recorder.record_command(cmd.strip())
        st.write(f"Recorded: {cmd.strip()}")

with col2:
    st.subheader("Checker")
    report = software_checker.run_checks()
    st.json(report)

st.subheader("Recent Recorded Commands")
cmds = dev_recorder.get_recent_commands(50)
if cmds:
    for c in cmds:
        st.text(c)
else:
    st.write("No recorded commands yet.")

st.caption("Logs and snapshots are stored under this folder (private): ./dev_session.log, ./env_snapshot.json")

# Download and maintenance actions
st.markdown("---")
colA, colB = st.columns(2)
with colA:
    if st.button("Download latest log"):
        # prefer compressed rotated files if present
        logfile = os.path.join(os.path.dirname(__file__), "dev_session.log")
        gz_candidates = sorted([p for p in os.listdir(os.path.dirname(__file__)) if p.startswith("dev_session.log.") and p.endswith(".gz")])
        data = None
        path_used = logfile
        if gz_candidates:
            path_used = os.path.join(os.path.dirname(__file__), gz_candidates[-1])
            with open(path_used, "rb") as f:
                data = f.read()
        elif os.path.exists(logfile):
            with open(logfile, "rb") as f:
                data = f.read()

        if data:
            st.download_button("Download log", data, file_name=os.path.basename(path_used), mime="application/gzip")
        else:
            st.warning("No log file found yet.")

with colB:
    if st.button("Force rotate logs (compress)"):
        dev_recorder.force_rotate()
        st.success("Rotation requested")
