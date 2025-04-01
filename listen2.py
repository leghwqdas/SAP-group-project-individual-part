#!/usr/bin/env python3

import rospy
from sensor_msgs.msg import JointState
from vosk import Model, KaldiRecognizer
import sounddevice as sd
import json

class OfflineKeywordListener:

    def __init__(self):
        rospy.init_node("miro_offline_keyword_listener")

        self.robot_name = rospy.get_param("~robot_name", "miro")

        # 初始化头部控制发布器
        self.pub_head = rospy.Publisher(
            f"/{self.robot_name}/control/kinematic_joints",
            JointState, queue_size=0
        )

        # 初始化尾巴控制发布器（可与头部共用话题）
        self.pub_tail = self.pub_head

        # 加载离线语音识别模型（路径根据你本地情况修改）
        self.model = Model(r"/home/mima1234/vosk-model")
        self.rec = KaldiRecognizer(self.model, 16000)

        self.triggered = False

        # 关键词到动作的映射
        self.keyword_actions = {
            "miro": self.action_shake_head,
            "mirror": self.action_shake_head,
            "hello": self.action_nod,
            "shake": self.action_shake_tail,
        }

        # 配置音频输入流
        self.stream = sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype='int16',
            channels=1,
            callback=self.audio_callback
        )

        rospy.loginfo("🎤 离线语音识别已启动，关键词有：%s", ", ".join(self.keyword_actions.keys()))

    def run(self):
        with self.stream:
            rospy.spin()

    def audio_callback(self, indata, frames, time, status):
        if self.rec.AcceptWaveform(bytes(indata)):
            result = self.rec.Result()
            text = json.loads(result).get("text", "").lower()
            rospy.loginfo("🧪 识别文本: %s", text)

            if not self.triggered:
                for keyword, action_fn in self.keyword_actions.items():
                    if keyword in text:
                        rospy.loginfo(f"🗣️ 识别到关键词：{keyword}")
                        self.triggered = True
                        action_fn()
                        rospy.Timer(rospy.Duration(3.0), self.reset_trigger, oneshot=True)
                        break

    def reset_trigger(self, event):
        self.triggered = False

    # ======= 动作函数 =======

    def action_shake_head(self):
        rospy.loginfo("🤖 执行：摇头")
        self.set_head(pitch=0.0, yaw=0.5)
        rospy.sleep(0.4)
        self.set_head(pitch=0.0, yaw=-0.5)
        rospy.sleep(0.4)
        self.set_head(pitch=0.0, yaw=0.0)

    def action_nod(self):
        rospy.loginfo("🤖 执行：点头")
        self.set_head(pitch=0.3, yaw=0.0)
        rospy.sleep(0.4)
        self.set_head(pitch=-0.3, yaw=0.0)
        rospy.sleep(0.4)
        self.set_head(pitch=0.0, yaw=0.0)

    def action_shake_tail(self):
        rospy.loginfo("🤖 执行：摇尾巴")
        msg = JointState()
        msg.name = ["joint_tail_yaw"]
        msg.position = [0.5]
        self.pub_tail.publish(msg)
        rospy.sleep(0.3)
        msg.position = [-0.5]
        self.pub_tail.publish(msg)
        rospy.sleep(0.3)
        msg.position = [0.0]
        self.pub_tail.publish(msg)

    # ======= 公共函数 =======

    def set_head(self, pitch=0.0, yaw=0.0):
        msg = JointState()
        msg.name = ["joint_head_lift", "joint_head_yaw", "joint_head_pitch", "joint_head_roll"]
        msg.position = [0.0, yaw, pitch, 0.0]
        self.pub_head.publish(msg)

if __name__ == "__main__":
    try:
        node = OfflineKeywordListener()
        node.run()
    except rospy.ROSInterruptException:
        pass
