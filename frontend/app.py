import streamlit as st
import requests
import io
import tempfile

# --- Configuration ---
API_BASE = "http://localhost:8000"  # Adjust for your deployment

st.set_page_config(page_title="🇴🇲 المُعالج الصوتي العُماني", layout="centered")
st.title("🇴🇲 المُعالج الصوتي العُماني")
st.markdown("**تحدث صوتيًا، استمع للإجابة، بدون تحميل ملفات**\n---")

# --- Session Management ---
if "session_id" not in st.session_state or "consent_text" not in st.session_state:
    try:
        resp = requests.post(f"{API_BASE}/start_session/")
        resp.raise_for_status()
        data = resp.json()
        st.session_state["session_id"] = data["session_id"]
        st.session_state["consent_text"] = data["consent_text"]
    except Exception:
        st.error("تعذر بدء جلسة جديدة. الرجاء إعادة المحاولة لاحقاً.")
        st.stop()

session_id = st.session_state["session_id"]
consent_text = st.session_state["consent_text"]

# --- Consent Gate ---
consent = st.checkbox(consent_text, value=False)
if not consent:
    st.warning("يرجى الموافقة أولًا على الشروط.")
    st.stop()

# --- Voice Input ---
try:
    audio_file = st.audio_input("🎤 سجل صوتك ثم اضغط إرسال")  # Streamlit >=1.33.0 only
except AttributeError:
    # Fallback for older versions
    audio_file = st.file_uploader("🎤 سجّل أو ارفع ملف صوتي (wav)", type=["wav", "mp3", "ogg"])

send_btn = st.button("أرسل الرسالة الصوتية")

feedback_box = st.empty()
audio_out_box = st.empty()

if send_btn:
    if not audio_file:
        feedback_box.error("يرجى تسجيل صوتك أولًا.")
    else:
        try:
            files = {'audio': ('voice.wav', io.BytesIO(audio_file.getbuffer()), 'audio/wav')}
            data = {'session_id': session_id}
            with st.spinner("يتم المعالجة ..."):
                resp = requests.post(f"{API_BASE}/chat/", files=files, data=data, timeout=90)
                resp.raise_for_status()
                result = resp.json()
                audio_url = result["bot_audio_url"]
                # Download and verify bot audio
                audio_resp = requests.get(audio_url)
                audio_resp.raise_for_status()
                # Debug info
                st.write(f"Audio URL: {audio_url}")
                st.write(f"Response status: {audio_resp.status_code}, length: {len(audio_resp.content)} bytes")

                if audio_resp.status_code == 200 and len(audio_resp.content) > 100:
                    # (Optional) Save for debugging—remove in production
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                        temp_audio.write(audio_resp.content)
                        temp_audio_path = temp_audio.name
                    st.info("تم إرسال الصوت بنجاح. استمع للرد.")
                    audio_out_box.audio(audio_resp.content, format="audio/wav")
                else:
                    feedback_box.error("لم يتم استلام صوت صحيح من الخادم.")
                    st.error(f"حجم الملف المستلم: {len(audio_resp.content)} بايت")
        except Exception as e:
            feedback_box.error("حدث خطأ أثناء المعالجة. الرجاء المحاولة مرة أخرى.")
            st.error(str(e))

st.markdown(
    "---\n"
    "⚠️ جميع الجلسات سرية بالكامل. إذا كنت تمر بأزمة نفسية أو عندك أفكار مؤذية، تواصل فورًا مع مختص أو الخط الساخن."
)
