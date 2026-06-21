/* ═══════════════════════════════════════════════════════════
   SpeakScorer — Audio Recorder (MediaRecorder API)
   ═══════════════════════════════════════════════════════════ */

class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.stream = null;
        this.isRecording = false;
        this.startTime = 0;
        this.timerInterval = null;
        this.audioBlob = null;
        this.audioUrl = null;
        this._stopResolve = null;
    }

    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: this._getSupportedMimeType(),
            });

            this.audioChunks = [];
            this.audioBlob = null;
            this.audioUrl = null;
            this._stopResolve = null;

            this.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    this.audioChunks.push(e.data);
                }
            };

            // TEK onstop: kayıt nasıl biterse bitsin (kullanıcı VEYA tarayıcı durdursa)
            // blob'u oluştur, kaynakları serbest bırak ve bekleyen stop() varsa çöz.
            this.mediaRecorder.onstop = () => {
                const mimeType = (this.mediaRecorder && this.mediaRecorder.mimeType) || 'audio/webm';
                this.audioBlob = new Blob(this.audioChunks, { type: mimeType });
                this.audioUrl = URL.createObjectURL(this.audioBlob);
                this.isRecording = false;
                this._stopTimer();
                this._stopStream();
                if (this._stopResolve) {
                    const r = this._stopResolve;
                    this._stopResolve = null;
                    r(this.audioBlob);
                }
            };

            this.mediaRecorder.start(200); // collect data every 200ms
            this.isRecording = true;
            this.startTime = Date.now();
            this._startTimer();

            return true;
        } catch (err) {
            console.error('Recording failed:', err);
            throw new Error('Microphone access denied. Please allow microphone permissions.');
        }
    }

    stop() {
        return new Promise((resolve) => {
            // Zaten durmuşsa (örn. tarayıcı kendisi durdurduysa) mevcut blob'u dön.
            if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
                this.isRecording = false;
                this._stopTimer();
                this._stopStream();
                resolve(this.audioBlob);
                return;
            }

            let settled = false;
            // Güvenlik ağı: onstop herhangi bir sebeple tetiklenmezse Promise asılı kalmasın.
            const safety = setTimeout(() => {
                if (settled) return;
                settled = true;
                this._stopResolve = null;
                this.isRecording = false;
                this._stopTimer();
                this._stopStream();
                resolve(this.audioBlob);
            }, 3000);

            // onstop (start'ta tanımlı) bu resolver'ı çağırır.
            this._stopResolve = (blob) => {
                if (settled) return;
                settled = true;
                clearTimeout(safety);
                resolve(blob);
            };

            try {
                this.mediaRecorder.stop();
            } catch (err) {
                clearTimeout(safety);
                if (!settled) {
                    settled = true;
                    this._stopResolve = null;
                    this.isRecording = false;
                    this._stopTimer();
                    this._stopStream();
                    resolve(this.audioBlob);
                }
            }
        });
    }

    getBlob() {
        return this.audioBlob;
    }

    getUrl() {
        return this.audioUrl;
    }

    getFile(filename = 'recording.webm') {
        if (!this.audioBlob) return null;
        return new File([this.audioBlob], filename, { type: this.audioBlob.type });
    }

    getElapsedTime() {
        if (!this.startTime) return '0:00';
        const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
        const m = Math.floor(elapsed / 60);
        const s = elapsed % 60;
        return `${m}:${s.toString().padStart(2, '0')}`;
    }

    _getSupportedMimeType() {
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/mp4',
        ];
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) return type;
        }
        return '';
    }

    _startTimer() {
        const display = document.getElementById('record-timer');
        if (!display) return;
        this.timerInterval = setInterval(() => {
            display.textContent = this.getElapsedTime();
        }, 1000);
    }

    _stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    _stopStream() {
        if (this.stream) {
            this.stream.getTracks().forEach(t => t.stop());
            this.stream = null;
        }
    }

    destroy() {
        this._stopTimer();
        this._stopStream();
        if (this.audioUrl) {
            URL.revokeObjectURL(this.audioUrl);
        }
    }
}
