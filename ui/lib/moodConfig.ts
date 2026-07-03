import type { LifeMood } from "./types";

export interface MoodConfig {
  label: string;
  emoji: string;
  color: string;
}

export const MOOD_CONFIG: Record<LifeMood, MoodConfig> = {
  happy:   { label: "Happy",   emoji: "😊", color: "#26a69a" },
  excited: { label: "Excited", emoji: "🤩", color: "#e6a800" },
  calm:    { label: "Calm",    emoji: "😌", color: "#42a5f5" },
  sad:     { label: "Sad",     emoji: "😔", color: "#78909c" },
  anxious: { label: "Anxious", emoji: "😰", color: "#fb8c00" },
  angry:   { label: "Angry",   emoji: "😠", color: "#ef5350" },
};

export const LIFE_MOODS: LifeMood[] = ["happy", "excited", "calm", "sad", "anxious", "angry"];
