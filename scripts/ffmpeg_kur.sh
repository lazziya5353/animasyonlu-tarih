#!/usr/bin/env bash
# ffmpeg + ffprobe kurulumu: önce hazır derleme indirir (hızlı), olmazsa apt'ye süre sınırıyla düşer.
set -u
if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then echo "ffmpeg zaten var"; exit 0; fi
indir() {
  local url="$1" d; d=$(mktemp -d)
  echo "indiriliyor: $url"
  if timeout 120 curl -fsSL --retry 2 --connect-timeout 15 "$url" -o "$d/f.tar.xz" \
     && tar -xJf "$d/f.tar.xz" -C "$d"; then
    local b; b=$(dirname "$(find "$d" -type f -name ffmpeg -perm -u+x | head -1)")
    [ -x "$b/ffmpeg" ] && [ -x "$b/ffprobe" ] && sudo cp "$b/ffmpeg" "$b/ffprobe" /usr/local/bin/ && return 0
  fi
  return 1
}
indir "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz" \
 || indir "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" \
 || { echo "hazır derleme olmadı, apt deneniyor"; timeout 240 sudo apt-get install -y -qq ffmpeg \
      || (timeout 180 sudo apt-get update -qq && timeout 240 sudo apt-get install -y -qq ffmpeg); }
ffmpeg -version | head -1 && ffprobe -version | head -1
