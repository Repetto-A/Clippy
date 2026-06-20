"use client"

import type React from "react"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Upload, Scissors, Download, Undo, Redo, Play, Pause, SkipBack, SkipForward } from "lucide-react"
import { useState, useRef } from "react"
import { ExportDialog } from "./export-dialog"
import { useMedia } from "@/contexts/media-context"
import { toast } from "@/hooks/use-toast"

export function Toolbar() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [canUndo, setCanUndo] = useState(false)
  const [canRedo, setCanRedo] = useState(false)
  const [showExportDialog, setShowExportDialog] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { addMediaFile } = useMedia()

  const handleImport = () => {
    fileInputRef.current?.click()
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (files) {
      for (const file of Array.from(files)) {
        const result = await addMediaFile(file)
        if (result.success) {
          toast({
            title: "File uploaded successfully",
            description: `${file.name} has been added to your media pool`,
          })
        } else {
          toast({
            title: "Upload failed",
            description: result.error,
            variant: "destructive",
          })
        }
      }
    }
    event.target.value = ""
  }

  const handleCut = () => {
    console.log("Cut action performed")
    setCanUndo(true)
  }

  const handleUndo = () => {
    console.log("Undo action performed")
    setCanRedo(true)
  }

  const handleRedo = () => {
    console.log("Redo action performed")
  }

  const handlePlay = () => {
    setIsPlaying(!isPlaying)
    console.log(isPlaying ? "Paused" : "Playing")
  }

  const handleExport = () => {
    setShowExportDialog(true)
  }

  return (
    <>
      <div className="h-14 border-b border-border bg-card px-4 flex items-center gap-2">
        {/* File Operations */}
        <Button variant="outline" size="sm" className="gap-2 bg-transparent" onClick={handleImport}>
          <Upload className="h-4 w-4" />
          Import
        </Button>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="video/*,image/*,audio/*"
          className="hidden"
          onChange={handleFileUpload}
        />

        <Button variant="outline" size="sm" className="gap-2 bg-transparent" onClick={handleExport}>
          <Download className="h-4 w-4" />
          Export
        </Button>

        <Separator orientation="vertical" className="h-6" />

        {/* Edit Operations */}
        <Button variant="outline" size="sm" className="gap-2 bg-transparent" onClick={handleCut}>
          <Scissors className="h-4 w-4" />
          Cut
        </Button>

        <Button variant="outline" size="sm" className="gap-2 bg-transparent" onClick={handleUndo} disabled={!canUndo}>
          <Undo className="h-4 w-4" />
          Undo
        </Button>

        <Button variant="outline" size="sm" className="gap-2 bg-transparent" onClick={handleRedo} disabled={!canRedo}>
          <Redo className="h-4 w-4" />
          Redo
        </Button>

        <Separator orientation="vertical" className="h-6" />

        {/* Playback Controls */}
        <Button variant="outline" size="sm">
          <SkipBack className="h-4 w-4" />
        </Button>

        <Button variant="default" size="sm" onClick={handlePlay}>
          {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>

        <Button variant="outline" size="sm">
          <SkipForward className="h-4 w-4" />
        </Button>

        <div className="flex-1" />

        {/* Timeline Position */}
        <div className="text-sm text-muted-foreground font-mono">00:00:00 / 00:00:00</div>
      </div>

      <ExportDialog open={showExportDialog} onOpenChange={setShowExportDialog} />
    </>
  )
}
