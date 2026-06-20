"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import {
  Plus,
  Volume2,
  VolumeX,
  Play,
  Pause,
  Scissors,
  Undo,
  Redo,
  Video,
  Music,
  Trash2,
  Eye,
  EyeOff,
  GripVertical,
  Edit2,
  Check,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react"
import { useState, useRef, useEffect } from "react"

interface Track {
  id: string
  name: string
  type: "video" | "audio"
  muted: boolean
  visible: boolean
  clips: Array<{
    id: string
    name: string
    start: number
    duration: number
    mediaId?: string
    mediaType?: "video" | "image" | "audio"
  }>
}

export function Timeline() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [canUndo, setCanUndo] = useState(false)
  const [canRedo, setCanRedo] = useState(false)
  const [draggedTrack, setDraggedTrack] = useState<string | null>(null)
  const [editingTrack, setEditingTrack] = useState<string | null>(null)
  const [editingName, setEditingName] = useState("")
  const [zoomLevel, setZoomLevel] = useState(1)
  const [playheadPosition, setPlayheadPosition] = useState(0) // Added playhead position state
  const minZoom = 0.25
  const maxZoom = 4

  const trackLabelsScrollRef = useRef<HTMLDivElement>(null)
  const timelineGridScrollRef = useRef<HTMLDivElement>(null)
  const playbackIntervalRef = useRef<NodeJS.Timeout | null>(null) // Added playback interval ref

  const [tracks, setTracks] = useState<Track[]>([])

  useEffect(() => {
    if (isPlaying) {
      playbackIntervalRef.current = setInterval(() => {
        setPlayheadPosition((prev) => prev + 1) // Move playhead 1 pixel per 100ms
      }, 100)
    } else {
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current)
        playbackIntervalRef.current = null
      }
    }

    return () => {
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current)
      }
    }
  }, [isPlaying])

  useEffect(() => {
    const handleTimelinePlay = (event: CustomEvent) => {
      setIsPlaying(event.detail.isPlaying)
    }

    window.addEventListener("timelinePlayback", handleTimelinePlay as EventListener)
    return () => window.removeEventListener("timelinePlayback", handleTimelinePlay as EventListener)
  }, [])

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev * 1.5, maxZoom))
  }

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev / 1.5, minZoom))
  }

  const resetZoom = () => {
    setZoomLevel(1)
  }

  const getScaledWidth = (width: number) => width * zoomLevel
  const getScaledPosition = (position: number) => position * zoomLevel
  const timelineWidth = getScaledWidth(1200)
  const timeMarkerSpacing = getScaledWidth(60)

  const handleScroll = (source: "labels" | "grid", scrollTop: number) => {
    if (source === "labels" && timelineGridScrollRef.current) {
      timelineGridScrollRef.current.scrollTop = scrollTop
    } else if (source === "grid" && trackLabelsScrollRef.current) {
      trackLabelsScrollRef.current.scrollTop = scrollTop
    }
  }

  const handleCut = () => {
    console.log("Timeline cut action performed")
    setCanUndo(true)
  }

  const handleUndo = () => {
    console.log("Timeline undo action performed")
    setCanRedo(true)
  }

  const handleRedo = () => {
    console.log("Timeline redo action performed")
  }

  const handlePlay = () => {
    const newPlayingState = !isPlaying
    setIsPlaying(newPlayingState)

    // Notify video preview component about timeline playback state
    window.dispatchEvent(
      new CustomEvent("timelinePlayback", {
        detail: { isPlaying: newPlayingState, playheadPosition },
      }),
    )

    console.log(newPlayingState ? "Timeline Playing" : "Timeline Paused")
  }

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const clickX = e.clientX - rect.left
    setPlayheadPosition(clickX / zoomLevel)
  }

  const addTrack = (type: "video" | "audio") => {
    const newTrack: Track = {
      id: Date.now().toString(),
      name: `${type === "video" ? "Video" : "Audio"} ${tracks.filter((t) => t.type === type).length + 1}`,
      type,
      muted: false,
      visible: true,
      clips: [],
    }
    setTracks([...tracks, newTrack])
  }

  const deleteTrack = (trackId: string) => {
    setTracks(tracks.filter((t) => t.id !== trackId))
  }

  const toggleTrackMute = (trackId: string) => {
    setTracks(tracks.map((t) => (t.id === trackId ? { ...t, muted: !t.muted } : t)))
  }

  const toggleTrackVisibility = (trackId: string) => {
    setTracks(tracks.map((t) => (t.id === trackId ? { ...t, visible: !t.visible } : t)))
  }

  const handleDragStart = (e: React.DragEvent, trackId: string) => {
    setDraggedTrack(trackId)
    e.dataTransfer.effectAllowed = "move"
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "move"
  }

  const handleDrop = (e: React.DragEvent, targetTrackId: string) => {
    e.preventDefault()
    if (!draggedTrack || draggedTrack === targetTrackId) return

    const draggedIndex = tracks.findIndex((t) => t.id === draggedTrack)
    const targetIndex = tracks.findIndex((t) => t.id === targetTrackId)

    const newTracks = [...tracks]
    const [draggedItem] = newTracks.splice(draggedIndex, 1)
    newTracks.splice(targetIndex, 0, draggedItem)

    setTracks(newTracks)
    setDraggedTrack(null)
  }

  const handleDragEnd = () => {
    setDraggedTrack(null)
  }

  const startEditingTrack = (trackId: string, currentName: string) => {
    setEditingTrack(trackId)
    setEditingName(currentName)
  }

  const saveTrackName = (trackId: string) => {
    if (editingName.trim()) {
      setTracks(tracks.map((t) => (t.id === trackId ? { ...t, name: editingName.trim() } : t)))
    }
    setEditingTrack(null)
    setEditingName("")
  }

  const cancelEditingTrack = () => {
    setEditingTrack(null)
    setEditingName("")
  }

  const handleMediaDrop = (e: React.DragEvent, trackId: string) => {
    e.preventDefault()

    try {
      const data = JSON.parse(e.dataTransfer.getData("application/json"))
      if (data.type === "media") {
        setTracks((currentTracks) => {
          const track = currentTracks.find((t) => t.id === trackId)
          if (!track) return currentTracks

          // Check if media type matches track type (or allow images on video tracks)
          if (
            (track.type === "video" && (data.mediaType === "video" || data.mediaType === "image")) ||
            (track.type === "audio" && data.mediaType === "audio")
          ) {
            const newClip = {
              id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
              name: data.title,
              start: 0, // Place at beginning for now
              duration: data.duration || 120, // Default duration if not provided
              mediaId: data.mediaId,
              mediaType: data.mediaType,
            }

            return currentTracks.map((t) => (t.id === trackId ? { ...t, clips: [...t.clips, newClip] } : t))
          }

          return currentTracks
        })

        console.log("Media dropped successfully:", data.title)
      }
    } catch (error) {
      console.error("Failed to parse drop data:", error)
    }
  }

  return (
    <div className="h-full flex flex-col bg-card">
      {/* Timeline Header */}
      <div className="h-12 border-b border-border px-4 flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2 bg-transparent">
              <Plus className="h-4 w-4" />
              Add Track
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={() => addTrack("video")} className="gap-2">
              <Video className="h-4 w-4" />
              Video Track
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => addTrack("audio")} className="gap-2">
              <Music className="h-4 w-4" />
              Audio Track
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Separator orientation="vertical" className="h-6" />

        <Button variant="outline" size="sm" onClick={handlePlay} className="bg-transparent">
          {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>

        <Button variant="outline" size="sm" onClick={handleCut} className="bg-transparent">
          <Scissors className="h-4 w-4" />
        </Button>

        <Button variant="outline" size="sm" onClick={handleUndo} disabled={!canUndo} className="bg-transparent">
          <Undo className="h-4 w-4" />
        </Button>

        <Button variant="outline" size="sm" onClick={handleRedo} disabled={!canRedo} className="bg-transparent">
          <Redo className="h-4 w-4" />
        </Button>

        <Separator orientation="vertical" className="h-6" />

        <div className="text-sm font-medium">Timeline</div>

        <div className="flex-1" />

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleZoomOut}
            disabled={zoomLevel <= minZoom}
            className="bg-transparent"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <button
            onClick={resetZoom}
            className="text-sm text-muted-foreground w-12 text-center hover:text-foreground transition-colors cursor-pointer"
          >
            {Math.round(zoomLevel * 100)}%
          </button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleZoomIn}
            disabled={zoomLevel >= maxZoom}
            className="bg-transparent"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Timeline Content */}
      <div className="flex-1 flex min-h-0">
        {/* Track Labels */}
        <div className="w-40 border-r border-border bg-muted/30 flex flex-col">
          <div className="h-12 border-b border-border flex items-center px-3 flex-shrink-0">
            <span className="text-sm font-medium">Tracks</span>
          </div>

          <div className="flex-1 overflow-hidden">
            <ScrollArea
              className="h-full"
              onScrollCapture={(e) => {
                const target = e.target as HTMLDivElement
                handleScroll("labels", target.scrollTop)
              }}
            >
              <div ref={trackLabelsScrollRef}>
                {tracks.length === 0 ? (
                  <div className="h-32 flex items-center justify-center text-muted-foreground text-sm">
                    No tracks yet
                  </div>
                ) : (
                  tracks.map((track) => (
                    <div
                      key={track.id}
                      className={`h-16 border-b border-border flex items-center px-2 gap-2 group cursor-move transition-colors ${
                        draggedTrack === track.id ? "bg-muted/50" : "hover:bg-muted/20"
                      }`}
                      draggable
                      onDragStart={(e) => handleDragStart(e, track.id)}
                      onDragOver={handleDragOver}
                      onDrop={(e) => handleDrop(e, track.id)}
                      onDragEnd={handleDragEnd}
                    >
                      <GripVertical className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />

                      <div className={`w-3 h-3 rounded ${track.type === "video" ? "bg-blue-500" : "bg-green-500"}`} />

                      {editingTrack === track.id ? (
                        <div className="flex-1 flex items-center gap-1">
                          <Input
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            className="h-6 text-xs"
                            onKeyDown={(e) => {
                              if (e.key === "Enter") saveTrackName(track.id)
                              if (e.key === "Escape") cancelEditingTrack()
                            }}
                            autoFocus
                          />
                          <Button
                            variant="ghost"
                            size="sm"
                            className="p-1 h-6 w-6"
                            onClick={() => saveTrackName(track.id)}
                          >
                            <Check className="h-3 w-3" />
                          </Button>
                          <Button variant="ghost" size="sm" className="p-1 h-6 w-6" onClick={cancelEditingTrack}>
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      ) : (
                        <span
                          className="text-sm flex-1 truncate cursor-pointer hover:text-foreground/80"
                          onClick={() => startEditingTrack(track.id, track.name)}
                        >
                          {track.name}
                        </span>
                      )}

                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {editingTrack !== track.id && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="p-1 h-6 w-6"
                            onClick={() => startEditingTrack(track.id, track.name)}
                          >
                            <Edit2 className="h-3 w-3" />
                          </Button>
                        )}

                        {track.type === "video" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="p-1 h-6 w-6"
                            onClick={() => toggleTrackVisibility(track.id)}
                          >
                            {track.visible ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
                          </Button>
                        )}

                        <Button
                          variant="ghost"
                          size="sm"
                          className="p-1 h-6 w-6"
                          onClick={() => toggleTrackMute(track.id)}
                        >
                          {track.muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          className="p-1 h-6 w-6 text-destructive hover:text-destructive"
                          onClick={() => deleteTrack(track.id)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>
        </div>

        {/* Timeline Grid */}
        <div className="flex-1 flex flex-col min-w-0">
          <div
            className="h-12 border-b border-border bg-muted/20 relative flex-shrink-0 overflow-x-auto cursor-pointer"
            onClick={handleTimelineClick}
          >
            {Array.from({ length: Math.ceil(20 * zoomLevel) }, (_, i) => (
              <div
                key={i}
                className="absolute top-0 bottom-0 border-l border-border/50"
                style={{ left: `${i * timeMarkerSpacing}px` }}
              >
                <span className="absolute top-1 left-1 text-xs text-muted-foreground">
                  {Math.floor(i / (2 * zoomLevel))}:{Math.round((i % (2 * zoomLevel)) * (30 / zoomLevel))}
                </span>
              </div>
            ))}
          </div>

          <div className="flex-1 overflow-hidden">
            <ScrollArea
              className="h-full"
              onScrollCapture={(e) => {
                const target = e.target as HTMLDivElement
                handleScroll("grid", target.scrollTop)
              }}
            >
              <div ref={timelineGridScrollRef} className="overflow-x-auto">
                <div className="relative" style={{ minWidth: `${timelineWidth}px` }}>
                  {tracks.length === 0 ? (
                    <div className="h-32 flex items-center justify-center text-muted-foreground text-sm border-b border-border">
                      Add tracks and drag media here to start editing
                    </div>
                  ) : (
                    tracks.map((track) => (
                      <div
                        key={track.id}
                        className="h-16 border-b border-border relative bg-background"
                        onDragOver={(e) => {
                          e.preventDefault()
                          e.dataTransfer.dropEffect = "copy"
                        }}
                        onDrop={(e) => handleMediaDrop(e, track.id)}
                      >
                        {track.clips.map((clip) => (
                          <div
                            key={clip.id}
                            className={`absolute top-2 bottom-2 rounded border flex items-center px-2 cursor-pointer transition-colors ${
                              track.type === "video"
                                ? "bg-blue-500/80 border-blue-600 hover:bg-blue-500/90"
                                : "bg-green-500/80 border-green-600 hover:bg-green-500/90"
                            } ${!track.visible && track.type === "video" ? "opacity-50" : ""}`}
                            style={{
                              left: `${getScaledPosition(clip.start)}px`,
                              width: `${getScaledWidth(clip.duration)}px`,
                            }}
                            onClick={() => {
                              if (clip.mediaId) {
                                window.dispatchEvent(
                                  new CustomEvent("playMedia", {
                                    detail: { mediaId: clip.mediaId, mediaType: clip.mediaType },
                                  }),
                                )
                              }
                            }}
                          >
                            <span className="text-xs text-white font-medium truncate">{clip.name}</span>
                            {clip.mediaType === "image" && <span className="ml-1 text-xs text-white/70">📷</span>}
                          </div>
                        ))}
                      </div>
                    ))
                  )}

                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10 pointer-events-none"
                    style={{ left: `${getScaledPosition(playheadPosition)}px` }}
                  >
                    <div className="absolute -top-1 -left-1 w-2 h-2 bg-red-500 rounded-full" />
                  </div>
                </div>
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
    </div>
  )
}
