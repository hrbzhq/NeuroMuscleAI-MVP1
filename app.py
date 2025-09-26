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
    st.subheader("Environment Checker")
    auto_fix = st.checkbox("Auto-fix issues", value=False)
    
    if st.button("Run Environment Check"):
        with st.spinner("Running checks..."):
            report = software_checker.run_checks(auto_fix=auto_fix)
        
        # Display status
        if report.get('fixes_applied'):
            st.success(f"✅ Fixes applied: {', '.join(report['fixes_applied'])}")
        
        if report.get('missing_packages'):
            st.warning(f"⚠️ Missing packages: {', '.join(report['missing_packages'])}")
        
        if report.get('git_dirty') is True:
            st.info("ℹ️ Uncommitted changes detected")
        
        st.json(report)

# New: Development Analysis Section
st.markdown("---")
st.subheader("📊 Development Analysis")

col3, col4 = st.columns(2)

with col3:
    if st.button("Generate Analysis Report"):
        try:
            import dev_analyzer
            analyzer = dev_analyzer.DevAnalyzer()
            insights = analyzer.generate_insights()
            
            if insights:
                st.success("🔍 Analysis Complete!")
                for insight in insights:
                    st.write(f"• {insight}")
            else:
                st.info("No significant insights found.")
                
            # Export reports
            json_report = analyzer.export_report('json')
            md_report = analyzer.export_report('md')
            
            st.write(f"📄 Reports generated:")
            st.write(f"• JSON: `{json_report}`")
            st.write(f"• Markdown: `{md_report}`")
            
        except Exception as e:
            st.error(f"Error generating analysis: {e}")

            
            
        # Attempt to generate and display charts (if available)
        try:
            # generate_charts returns a mapping of name->filename
            images = {}
            if hasattr(dev_analyzer, 'HAS_PLOTTING') and dev_analyzer.HAS_PLOTTING:
                try:
                    images = analyzer.generate_charts()
                except Exception:
                    images = {}

            if images:
                st.markdown("---")
                st.subheader("Generated Charts")
                # Create a responsive 2-column grid for images
                img_items = list(images.items())
                cols = None
                for i in range(0, len(img_items), 2):
                    left = img_items[i]
                    right = img_items[i+1] if i+1 < len(img_items) else None
                    c1, c2 = st.columns(2)

                    # Left image
                    key, img_name = left
                    candidates = [
                        os.path.join(os.path.dirname(__file__), img_name),
                        os.path.join(os.getcwd(), img_name),
                        img_name,
                    ]
                    img_path = None
                    for c in candidates:
                        if c and os.path.exists(c):
                            img_path = c
                            break

                    with c1:
                        if img_path:
                            try:
                                st.image(img_path, caption=key.replace('_', ' ').title())
                                with open(img_path, 'rb') as f:
                                    data = f.read()
                                st.download_button(f"Download {os.path.basename(img_path)}", data, file_name=os.path.basename(img_path), mime='image/png')
                            except Exception as e:
                                st.write(f"Could not display image {img_name}: {e}")
                        else:
                            st.write(f"Image file for {key} not found: {img_name}")

                    # Right image (if any)
                    if right:
                        key_r, img_name_r = right
                        candidates_r = [
                            os.path.join(os.path.dirname(__file__), img_name_r),
                            os.path.join(os.getcwd(), img_name_r),
                            img_name_r,
                        ]
                        img_path_r = None
                        for c in candidates_r:
                            if c and os.path.exists(c):
                                img_path_r = c
                                break

                        with c2:
                            if img_path_r:
                                try:
                                    st.image(img_path_r, caption=key_r.replace('_', ' ').title())
                                    with open(img_path_r, 'rb') as f:
                                        data_r = f.read()
                                    st.download_button(f"Download {os.path.basename(img_path_r)}", data_r, file_name=os.path.basename(img_path_r), mime='image/png')
                                except Exception as e:
                                    st.write(f"Could not display image {img_name_r}: {e}")
                            else:
                                st.write(f"Image file for {key_r} not found: {img_name_r}")
            else:
                if hasattr(dev_analyzer, 'HAS_PLOTTING') and not dev_analyzer.HAS_PLOTTING:
                    st.info("Plotting packages not available. Install matplotlib/pandas to generate charts.")
        except Exception as e:
            st.write(f"Error while loading charts: {e}")

with col4:
    if st.button("Run CI Pipeline"):
        try:
            import ci_pipeline
            pipeline = ci_pipeline.CIPipeline()
            
            with st.spinner("Running CI pipeline..."):
                results = pipeline.run_full_pipeline()
            
            status = results['overall_status']
            if status == 'passed':
                st.success("✅ CI Pipeline Passed!")
            else:
                st.error(f"❌ CI Pipeline Failed - Steps: {results.get('failed_steps', [])}")
            
            # Show step results
            for step, result in results['steps'].items():
                step_status = result.get('status', 'unknown')
                if step_status == 'passed':
                    st.write(f"✅ {step}: {step_status}")
                elif step_status == 'failed':
                    st.write(f"❌ {step}: {step_status}")
                else:
                    st.write(f"⚠️ {step}: {step_status}")
            
        except Exception as e:
            st.error(f"Error running CI pipeline: {e}")

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
