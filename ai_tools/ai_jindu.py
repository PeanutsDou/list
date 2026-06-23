
class AIProgress:
    """
    用于管理和报告 AI 任务进度的工具类。
    """
    def __init__(self):
        self.steps = []
        self.current_step = 0
        self.total_steps = 0

    def start_task(self, description, total_steps=1):
        self.steps = []
        self.current_step = 0
        self.total_steps = total_steps
        return f"开始任务: {description} (共 {total_steps} 步)"

    def update(self, step_description, step_increment=1):
        self.current_step += step_increment
        progress = min(100, int((self.current_step / self.total_steps) * 100)) if self.total_steps > 0 else 0
        msg = f"正在进行: {step_description} ... {progress}%"
        self.steps.append(msg)
        return msg

    def finish(self, message="任务完成"):
        self.current_step = self.total_steps
        return f"✅ {message}"

# 全局实例，供简单的跨模块调用 (如果需要)
global_progress = AIProgress()
