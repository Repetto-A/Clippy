"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Play, Pause, Volume2, VolumeX } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { useMedia } from "@/contexts/media-context"

export function VideoPreview() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [currentMedia, setCurrentMedia] = useState<string | null>(null)
  const [currentMediaType, setCurrentMediaType] = useState<"video" | "image" | "audio" | null>(null)
  const [timelinePlayback, setTimelinePlayback] = useState(false) // Added timeline playback state
  const videoRef = useRef<HTMLVideoElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const { getMediaFile } = useMedia()

  useEffect(() => {
    const handlePlayMedia = (event: CustomEvent) => {
      const { mediaId, mediaType } = event.detail
      setCurrentMedia(mediaId)
      setCurrentMediaType(mediaType)
      setIsPlaying(true)
    }

    const handleTimelinePlayback = (event: CustomEvent) => {
      const { isPlaying: timelinePlaying } = event.detail
      setTimelinePlayback(timelinePlaying)

      // Sync video/audio playback with timeline
      if (currentMedia && currentMediaType) {
        if (timelinePlaying) {
          if (currentMediaType === "video" && videoRef.current) {
            videoRef.current.play()
          } else if (currentMediaType === "audio" && audioRef.current) {
            audioRef.current.play()
          }
          setIsPlaying(true)
        } else {
          if (currentMediaType === "video" && videoRef.current) {
            videoRef.current.pause()
          } else if (currentMediaType === "audio" && audioRef.current) {
            audioRef.current.pause()
          }
          setIsPlaying(false)
        }
      }
    }

    window.addEventListener("playMedia", handlePlayMedia as EventListener)
    window.addEventListener("timelinePlayback", handleTimelinePlayback as EventListener)

    return () => {
      window.removeEventListener("playMedia", handlePlayMedia as EventListener)
      window.removeEventListener("timelinePlayback", handleTimelinePlayback as EventListener)
    }
  }, [currentMedia, currentMediaType])

  const togglePlay = () => {
    if (currentMedia && currentMediaType) {
      const newPlayingState = !isPlaying

      if (currentMediaType === "video" && videoRef.current) {
        if (newPlayingState) {
          videoRef.current.play()
        } else {
          videoRef.current.pause()
        }
      } else if (currentMediaType === "audio" && audioRef.current) {
        if (newPlayingState) {
          audioRef.current.play()
        } else {
          audioRef.current.pause()
        }
      }

      setIsPlaying(newPlayingState)

      window.dispatchEvent(
        new CustomEvent("timelinePlayback", {
          detail: { isPlaying: newPlayingState },
        }),
      )
    }
  }

  const toggleMute = () => {
    if (videoRef.current) videoRef.current.muted = !isMuted
    if (audioRef.current) audioRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const mediaFile = currentMedia ? getMediaFile(currentMedia) : null

  return (
    <div className="flex-1 p-4 bg-muted/20">
      <Card className="h-full flex items-center justify-center bg-black/90 relative overflow-hidden">
        {/* Media content */}
        {mediaFile ? (
          <div className="absolute inset-0">
            {currentMediaType === "video" && (
              <video
                ref={videoRef}
                src={mediaFile.url}
                className="w-full h-full object-contain"
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                muted={isMuted}
              />
            )}
            {currentMediaType === "image" && (
              <img
                src={mediaFile.url || "/placeholder.svg"}
                alt={mediaFile.title}
                className="w-full h-full object-contain"
              />
            )}
            {currentMediaType === "audio" && (
              <div className="flex items-center justify-center h-full text-white">
                <div className="text-center">
                  <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-white/10 flex items-center justify-center">
                    <Volume2 className="h-8 w-8" />
                  </div>
                  <p className="text-lg font-medium">{mediaFile.title}</p>
                  <p className="text-sm opacity-75">Audio Track</p>
                </div>
                <audio
                  ref={audioRef}
                  src={mediaFile.url}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  muted={isMuted}
                />
              </div>
            )}
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-white/60">
              <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-white/10 flex items-center justify-center">
                <Play className="h-8 w-8 ml-1" />
              </div>
              <p className="text-lg font-medium">No media loaded</p>
              <p className="text-sm opacity-75">Drag media to timeline or click a clip to preview</p>
            </div>
          </div>
        )}

        {/* Video controls overlay */}
        <div className="absolute bottom-4 left-4 right-4 flex items-center gap-3">
          <Button
            size="sm"
            variant="secondary"
            className="bg-black/50 hover:bg-black/70 text-white border-white/20"
            onClick={togglePlay}
            disabled={!currentMedia}
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </Button>

          <div className="flex-1 h-1 bg-white/20 rounded-full">
            <div className="h-full w-1/3 bg-white rounded-full" />
          </div>

          <Button
            size="sm"
            variant="secondary"
            className="bg-black/50 hover:bg-black/70 text-white border-white/20"
            onClick={toggleMute}
            disabled={!currentMedia || currentMediaType === "image"}
          >
            {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </Button>

          <span className="text-white text-sm font-mono">
            {mediaFile
              ? currentMediaType === "video"
                ? "Video"
                : currentMediaType === "image"
                  ? "Image"
                  : "Audio"
              : "Ready"}
          </span>
        </div>
      </Card>
    </div>
  )
}
