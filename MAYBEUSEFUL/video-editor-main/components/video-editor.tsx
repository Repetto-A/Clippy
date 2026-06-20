"use client"

import type React from "react"

import { useState, useRef, useCallback } from "react"
import { Toolbar } from "./video-editor/toolbar"
import { VideoPreview } from "./video-editor/video-preview"
import { Timeline } from "./video-editor/timeline"
import { PropertiesPanel } from "./video-editor/properties-panel"
import { MediaProvider } from "@/contexts/media-context"

export function VideoEditor() {
  const [rightPanelWidth, setRightPanelWidth] = useState(320) // 320px default (w-80)
  const [isResizing, setIsResizing] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return

      const containerRect = containerRef.current.getBoundingClientRect()
      const newWidth = containerRect.right - e.clientX

      // Constrain width between 240px and 600px
      const constrainedWidth = Math.max(240, Math.min(600, newWidth))
      setRightPanelWidth(constrainedWidth)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
      document.removeEventListener("mousemove", handleMouseMove)
      document.removeEventListener("mouseup", handleMouseUp)
    }

    document.addEventListener("mousemove", handleMouseMove)
    document.addEventListener("mouseup", handleMouseUp)
  }, [])

  return (
    <MediaProvider>
      <div className="h-full w-full flex flex-col bg-background">
        {/* Top Toolbar */}
        <Toolbar />

        {/* Main Content Area */}
        <div ref={containerRef} className="flex-1 flex overflow-hidden">
          {/* Video Preview - Takes up remaining space */}
          <div className="flex-1 flex flex-col min-w-0" style={{ width: `calc(100% - ${rightPanelWidth}px)` }}>
            <VideoPreview />

            {/* Timeline at bottom */}
            <div className="h-64 border-t border-border">
              <Timeline />
            </div>
          </div>

          <div
            className={`w-1 bg-border hover:bg-primary/20 cursor-col-resize transition-colors ${
              isResizing ? "bg-primary/40" : ""
            }`}
            onMouseDown={handleMouseDown}
            role="separator"
            aria-label="Resize panels"
            aria-orientation="vertical"
          />

          <div className="border-l border-border flex-shrink-0" style={{ width: `${rightPanelWidth}px` }}>
            <PropertiesPanel />
          </div>
        </div>
      </div>
    </MediaProvider>
  )
}
