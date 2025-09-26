"""Development Session Analyzer.

Analyzes dev_session.log JSONL data to extract insights about development patterns,
performance metrics, and system usage.
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
import statistics

try:
    import matplotlib.pyplot as plt
    import pandas as pd
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False


class DevAnalyzer:
    def __init__(self, log_path: str = None):
        if log_path is None:
            log_path = os.path.join(os.path.dirname(__file__), "dev_session.log")
        self.log_path = log_path
        self.events = []
        self.load_events()
    
    def load_events(self):
        """Load and parse JSONL events from the log file."""
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('---'):
                        try:
                            event = json.loads(line)
                            if 'timestamp' in event:
                                # Parse timestamp
                                event['parsed_timestamp'] = datetime.fromisoformat(
                                    event['timestamp'].replace('Z', '+00:00')
                                )
                            self.events.append(event)
                        except json.JSONDecodeError:
                            continue
        except FileNotFoundError:
            print(f"Log file not found: {self.log_path}")
    
    def analyze_session_patterns(self) -> Dict[str, Any]:
        """Analyze development session patterns."""
        if not self.events:
            return {"error": "No events found"}
        
        analysis = {}
        
        # Event type frequency
        event_types = Counter(event.get('type', 'unknown') for event in self.events)
        analysis['event_frequency'] = dict(event_types)
        
        # Session duration analysis
        sessions = []
        current_session_start = None
        
        for event in self.events:
            if event.get('type') == 'session-start':
                current_session_start = event.get('parsed_timestamp')
            elif event.get('type') == 'session-stop' and current_session_start:
                duration = event.get('parsed_timestamp') - current_session_start
                sessions.append(duration.total_seconds() / 3600)  # Convert to hours
                current_session_start = None
        
        if sessions:
            analysis['session_stats'] = {
                'total_sessions': len(sessions),
                'avg_duration_hours': statistics.mean(sessions),
                'max_duration_hours': max(sessions),
                'min_duration_hours': min(sessions)
            }
        
        # Command analysis
        commands = []
        for event in self.events:
            if event.get('type') == 'cmd' and 'payload' in event:
                cmd = event['payload'].get('command', '')
                if cmd:
                    commands.append(cmd.split()[0] if cmd.split() else cmd)
        
        if commands:
            analysis['command_frequency'] = dict(Counter(commands).most_common(10))
        
        # System resource trends
        cpu_usage = []
        memory_usage = []
        
        for event in self.events:
            if event.get('type') == 'snapshot' and 'payload' in event:
                payload = event['payload']
                if 'cpu_percent' in payload:
                    cpu_usage.append(payload['cpu_percent'])
                if 'memory_percent' in payload:
                    memory_usage.append(payload['memory_percent'])
        
        if cpu_usage:
            analysis['resource_usage'] = {
                'avg_cpu_percent': statistics.mean(cpu_usage),
                'max_cpu_percent': max(cpu_usage),
                'avg_memory_percent': statistics.mean(memory_usage) if memory_usage else 0,
                'max_memory_percent': max(memory_usage) if memory_usage else 0
            }
        
        # Time-based activity analysis
        if self.events:
            start_time = min(event.get('parsed_timestamp') for event in self.events if event.get('parsed_timestamp'))
            end_time = max(event.get('parsed_timestamp') for event in self.events if event.get('parsed_timestamp'))
            analysis['activity_period'] = {
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'total_days': (end_time - start_time).days if start_time and end_time else 0
            }
        
        return analysis
    
    def generate_insights(self) -> List[str]:
        """Generate actionable insights from the analysis."""
        analysis = self.analyze_session_patterns()
        insights = []
        
        # Session insights
        if 'session_stats' in analysis:
            stats = analysis['session_stats']
            avg_hours = stats['avg_duration_hours']
            if avg_hours > 8:
                insights.append("⚠️  Long development sessions detected (>8h). Consider taking breaks.")
            elif avg_hours < 1:
                insights.append("💡 Short sessions detected. Consider batching related tasks.")
        
        # Resource insights
        if 'resource_usage' in analysis:
            resources = analysis['resource_usage']
            if resources['max_cpu_percent'] > 80:
                insights.append("🔥 High CPU usage detected. Consider optimizing compute-intensive tasks.")
            if resources['max_memory_percent'] > 85:
                insights.append("💾 High memory usage detected. Monitor for memory leaks.")
        
        # Command insights
        if 'command_frequency' in analysis:
            commands = analysis['command_frequency']
            if 'python' in commands and commands['python'] > 20:
                insights.append("🐍 Heavy Python usage detected. Consider setting up persistent environments.")
            if 'git' in commands and commands['git'] > 15:
                insights.append("🔄 Frequent git operations. Consider using git aliases or automation.")
        
        # Activity insights
        if 'event_frequency' in analysis:
            events = analysis['event_frequency']
            if events.get('heartbeat', 0) > 1000:
                insights.append("💓 High activity level detected. Great development momentum!")
        
        return insights

    def _top_files(self, n=10) -> List[Tuple[str, int]]:
        """Return top referenced or changed files based on events payloads."""
        counter = Counter()
        for event in self.events:
            payload = event.get('payload', {})
            # payload may include 'path' or 'files'
            if isinstance(payload, dict):
                if 'path' in payload and isinstance(payload['path'], str):
                    counter[payload['path']] += 1
                if 'files' in payload and isinstance(payload['files'], list):
                    for f in payload['files']:
                        counter[f] += 1
        return counter.most_common(n)

    def generate_charts(self) -> Dict[str, str]:
        """Generate charts (PNG) from events and return mapping name->path."""
        if not HAS_PLOTTING:
            return {}

        # Prepare timeseries for CPU and memory
        times = []
        cpu = []
        mem = []
        for ev in self.events:
            if ev.get('type') == 'snapshot' and 'payload' in ev:
                ts = ev.get('parsed_timestamp')
                if not ts:
                    continue
                times.append(ts)
                payload = ev['payload']
                cpu.append(payload.get('cpu_percent', None))
                mem.append(payload.get('memory_percent', None))

        images = {}
        # CPU/Memory time series
        if times and any(v is not None for v in cpu+mem):
            try:
                plt.figure(figsize=(10, 4))
                plt.plot(times, cpu, label='CPU %')
                plt.plot(times, mem, label='Memory %')
                plt.legend()
                plt.xlabel('Time')
                plt.ylabel('Percent')
                plt.tight_layout()
                cpu_img = 'dev_cpu_mem.png'
                plt.savefig(cpu_img)
                plt.close()
                images['cpu_memory'] = cpu_img
            except Exception:
                pass

        # Command frequency bar chart
        commands = [ev['payload'].get('command', '').split()[0] for ev in self.events if ev.get('type') == 'cmd' and ev.get('payload')]
        if commands:
            try:
                cmd_counts = Counter(commands)
                top_cmds = cmd_counts.most_common(12)
                labels, counts = zip(*top_cmds)
                plt.figure(figsize=(8, 4))
                plt.bar(labels, counts)
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                cmd_img = 'dev_top_commands.png'
                plt.savefig(cmd_img)
                plt.close()
                images['top_commands'] = cmd_img
            except Exception:
                pass

        # Activity timeline: events count per hour
        try:
            hours = defaultdict(int)
            for ev in self.events:
                ts = ev.get('parsed_timestamp')
                if ts:
                    h = ts.replace(minute=0, second=0, microsecond=0)
                    hours[h] += 1
            if hours:
                ks = sorted(hours.keys())
                vs = [hours[k] for k in ks]
                plt.figure(figsize=(10, 3))
                plt.plot(ks, vs, marker='o')
                plt.tight_layout()
                tl_img = 'dev_activity_timeline.png'
                plt.savefig(tl_img)
                plt.close()
                images['activity_timeline'] = tl_img
        except Exception:
            pass

        # Top files touched
        top_files = self._top_files(12)
        if top_files:
            try:
                labels, counts = zip(*top_files)
                plt.figure(figsize=(8, 4))
                plt.barh(labels, counts)
                plt.tight_layout()
                files_img = 'dev_top_files.png'
                plt.savefig(files_img)
                plt.close()
                images['top_files'] = files_img
            except Exception:
                pass

        return images
    
    def export_report(self, format='json', output_path=None) -> str:
        """Export analysis report in specified format."""
        analysis = self.analyze_session_patterns()
        insights = self.generate_insights()
        # Attempt to generate charts if plotting available
        images = {}
        if HAS_PLOTTING:
            try:
                images = self.generate_charts()
            except Exception:
                images = {}

        report = {
            'analysis': analysis,
            'insights': insights,
            'generated_at': datetime.now().isoformat(),
            'total_events': len(self.events),
            'images': images,
        }
        
        if output_path is None:
            output_path = f"dev_analysis_report.{format}"
        
        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        elif format == 'md':
            self._export_markdown_report(report, output_path)
        
        return output_path
    
    def _export_markdown_report(self, report: Dict, output_path: str):
        """Export report as markdown."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Development Session Analysis Report\n\n")
            f.write(f"**Generated:** {report['generated_at']}  \n")
            f.write(f"**Total Events:** {report['total_events']}  \n\n")
            
            # Insights
            f.write("## 🔍 Key Insights\n\n")
            for insight in report['insights']:
                f.write(f"- {insight}\n")
            f.write("\n")
            
            # Analysis details
            analysis = report['analysis']
            
            if 'session_stats' in analysis:
                f.write("## 📊 Session Statistics\n\n")
                stats = analysis['session_stats']
                f.write(f"- **Total Sessions:** {stats['total_sessions']}\n")
                f.write(f"- **Average Duration:** {stats['avg_duration_hours']:.2f} hours\n")
                f.write(f"- **Max Duration:** {stats['max_duration_hours']:.2f} hours\n\n")
            
            if 'command_frequency' in analysis:
                f.write("## 🔧 Most Used Commands\n\n")
                for cmd, count in analysis['command_frequency'].items():
                    f.write(f"- **{cmd}:** {count} times\n")
                f.write("\n")
            
            if 'resource_usage' in analysis:
                f.write("## 💻 Resource Usage\n\n")
                res = analysis['resource_usage']
                f.write(f"- **Average CPU:** {res['avg_cpu_percent']:.1f}%\n")
                f.write(f"- **Peak CPU:** {res['max_cpu_percent']:.1f}%\n")
                f.write(f"- **Average Memory:** {res['avg_memory_percent']:.1f}%\n")
                f.write(f"- **Peak Memory:** {res['max_memory_percent']:.1f}%\n\n")


def main():
    """CLI interface for the analyzer."""
    analyzer = DevAnalyzer()
    
    print("🔍 Development Session Analysis")
    print("=" * 40)
    
    # Generate insights
    insights = analyzer.generate_insights()
    if insights:
        print("\n💡 Key Insights:")
        for insight in insights:
            print(f"  {insight}")
    
    # Export reports
    json_report = analyzer.export_report('json')
    md_report = analyzer.export_report('md')
    
    print(f"\n📄 Reports generated:")
    print(f"  - JSON: {json_report}")
    print(f"  - Markdown: {md_report}")


if __name__ == "__main__":
    main()