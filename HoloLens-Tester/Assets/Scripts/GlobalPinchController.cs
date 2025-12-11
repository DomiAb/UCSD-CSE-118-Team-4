using UnityEngine;
using UnityEngine.XR.Hands;
using UnityEngine.XR.Management;

public class GlobalPinchController : MonoBehaviour
{
    public HoloLensSpeechSender sender;

    XRHandSubsystem handSubsystem;

    // Pinch thresholds (engage < release)
    private const float pinchEngageDist = 0.025f;  // 2.5 cm to START pinch
    private const float pinchReleaseDist = 0.035f; // 3.5 cm to END pinch
    private const float pinchStableDelay = 0.10f;  // 100ms stable pinch

    // Per-hand stable pinch states
    private bool leftPinching = false;
    private bool rightPinching = false;

    // Per-hand debounce timers
    private float leftPinchStartTime = 0f;
    private float rightPinchStartTime = 0f;

    void Start()
    {
        handSubsystem = XRGeneralSettings.Instance?
            .Manager?.activeLoader?
            .GetLoadedSubsystem<XRHandSubsystem>();

        Debug.Log("XRHandSubsystem loaded: " + (handSubsystem != null));
    }

    void Update()
    {
        if (handSubsystem == null) return;

        HandleHand(
            handSubsystem.leftHand,
            ref leftPinching,
            ref leftPinchStartTime,
            onPinch: () => {
                sender.SendStartConversation();
                Debug.Log("START (left-hand pinch)");
            });

        HandleHand(
            handSubsystem.rightHand,
            ref rightPinching,
            ref rightPinchStartTime,
            onPinch: () => {
                sender.SendStopConversation();
                Debug.Log("STOP (right-hand pinch)");
            });
    }

    private void HandleHand(
        XRHand hand,
        ref bool isPinching,
        ref float pinchTime,
        System.Action onPinch)
    {
        bool raw = RawPinch(hand);

        if (!isPinching)
        {
            if (raw)
            {
                if (pinchTime == 0f)
                    pinchTime = Time.time;

                if (Time.time - pinchTime > pinchStableDelay)
                {
                    isPinching = true;
                    onPinch(); // trigger start/stop
                }
            }
            else
            {
                pinchTime = 0f;
            }
        }
        else
        {
            // release pinch
            if (!raw)
            {
                isPinching = false;
                pinchTime = 0f;
            }
        }
    }

    private bool RawPinch(XRHand hand)
    {
        if (!hand.isTracked) return false;

        XRHandJoint thumb = hand.GetJoint(XRHandJointID.ThumbTip);
        XRHandJoint index = hand.GetJoint(XRHandJointID.IndexTip);

        // Ensure tracked joint positions
        if ((thumb.trackingState == XRHandJointTrackingState.None)||
            (index.trackingState == XRHandJointTrackingState.None))
            return false;

        if (!thumb.TryGetPose(out Pose t)) return false;
        if (!index.TryGetPose(out Pose i)) return false;

        float d = Vector3.Distance(t.position, i.position);

        // hysteresis
        if (!leftPinching && !rightPinching)
            return d < pinchEngageDist;
        else
            return d < pinchReleaseDist;
    }
}
