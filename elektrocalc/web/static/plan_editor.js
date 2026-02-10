(() => {
  const canvas = document.getElementById("c");
  const ctx = canvas.getContext("2d");
  const toolSel = document.getElementById("tool");
  const pointTypeSel = document.getElementById("pointType");
  const roomTypeInp = document.getElementById("roomType");
  const roomNameInp = document.getElementById("roomName");
  const finishRoomBtn = document.getElementById("finishRoom");
  const finishRouteBtn = document.getElementById("finishRoute");
  const routeTypeSel = document.getElementById("routeType");
  const hint = document.getElementById("hint");
  const scaleText = document.getElementById("scaleText");

  let img = new Image();
  let imgLoaded = false;

  // camera
  let cam = { x: 0, y: 0, zoom: 1.0 };
  let dragging = false;
  let last = { x: 0, y: 0 };

  // tool states
  let scalePts = [];     // [{x,y},{x,y}]
  let roomPts = [];      // vertices in image coords
  let routePts = [];     // polyline points in image coords

  // existing routes from server (injected)
  const EXISTING_ROUTES = window.EXISTING_ROUTES || [];


  function screenToImage(px, py) {
    return {
      x: (px - cam.x) / cam.zoom,
      y: (py - cam.y) / cam.zoom
    };
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // background
    if (imgLoaded) {
      ctx.save();
      ctx.translate(cam.x, cam.y);
      ctx.scale(cam.zoom, cam.zoom);
      ctx.drawImage(img, 0, 0);
      ctx.restore();
    }

    // overlay: existing routes
    drawRoutes(EXISTING_ROUTES, "rgba(0,160,0,0.9)");

    // overlay: route in-progress
    if (routePts.length > 0) {
      drawPolyline(routePts, "rgba(0,160,0,0.9)", false);
      drawPoints(routePts, "rgba(0,160,0,0.9)");
    }

    // overlay: scale points
    drawPoints(scalePts, "rgba(180,0,0,0.9)");

    // overlay: room polygon in-progress
    if (roomPts.length > 0) {
      drawPolyline(roomPts, "rgba(0,100,200,0.9)", true);
      drawPoints(roomPts, "rgba(0,100,200,0.9)");
    }
  }

  function drawPoints(pts, color) {
    ctx.save();
    ctx.fillStyle = color;
    for (const p of pts) {
      const sx = p.x * cam.zoom + cam.x;
      const sy = p.y * cam.zoom + cam.y;
      ctx.beginPath();
      ctx.arc(sx, sy, 5, 0, Math.PI*2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawRoutes(routes, color) {
    if (!routes) return;
    for (const r of routes) {
      const pts = (r.polyline_px && r.polyline_px.points) ? r.polyline_px.points.map(p => ({x:p.x, y:p.y})) : [];
      drawPolyline(pts, color, false);
    }
  }

  function drawPolyline(pts, color, closed=false) {
    if (pts.length < 2) return;
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    const p0 = pts[0];
    ctx.moveTo(p0.x * cam.zoom + cam.x, p0.y * cam.zoom + cam.y);
    for (let i=1;i<pts.length;i++) {
      const p = pts[i];
      ctx.lineTo(p.x * cam.zoom + cam.x, p.y * cam.zoom + cam.y);
    }
    if (closed && pts.length >= 3) {
      ctx.lineTo(p0.x * cam.zoom + cam.x, p0.y * cam.zoom + cam.y);
    }
    ctx.stroke();
    ctx.restore();
  }

  function setHint() {
    const t = toolSel.value;
    if (t === "pan") hint.textContent = "Maus ziehen = bewegen, Mausrad = zoom.";
    if (t === "scale") hint.textContent = "Klicke 2 Punkte (bekannte Distanz), danach Eingabe in Meter.";
    if (t === "room") hint.textContent = "Klicke Punkte für Polygon. 'Raum abschließen' zum Speichern.";
    if (t === "point") hint.textContent = "Klicke zum Setzen eines Punkts des gewählten Typs.";
    if (t === "route") hint.textContent = "Klicke Punkte für einen Leitungsweg (Polyline). \"Leitungsweg abschließen\" zum Speichern.";
  }

  toolSel.addEventListener("change", () => {
    scalePts = [];
    roomPts = [];
    routePts = [];
    setHint();
    draw();
  });

  finishRouteBtn.addEventListener("click", async () => {
    if (toolSel.value !== "route") return;
    if (routePts.length < 2) { alert("Mindestens 2 Punkte für eine Route."); return; }
    const payload = {
      route_type: routeTypeSel.value,
      polyline_px: { points: routePts.map(p => ({x: Math.round(p.x), y: Math.round(p.y)})) },
      attributes: {}
    };
    const res = await fetch(`/api/plans/${PLAN_ID}/routes`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    if (!res.ok) { alert("Route speichern fehlgeschlagen."); return; }
    location.reload();
  });

  finishRoomBtn.addEventListener("click", async () => {
    if (toolSel.value !== "room") return;
    if (roomPts.length < 3) { alert("Mindestens 3 Punkte für einen Raum."); return; }
    const payload = {
      room_type: roomTypeInp.value.trim() || "WOHNEN",
      name: roomNameInp.value.trim() || null,
      polygon_px: { points: roomPts.map(p => ({x: Math.round(p.x), y: Math.round(p.y)})) }
    };
    const res = await fetch(`/api/plans/${PLAN_ID}/rooms`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      alert("Speichern fehlgeschlagen.");
      return;
    }
    location.reload();
  });

  canvas.addEventListener("mousedown", (e) => {
    if (toolSel.value === "pan") {
      dragging = true;
      last = { x: e.offsetX, y: e.offsetY };
    }
  });
  canvas.addEventListener("mouseup", () => dragging = false);
  canvas.addEventListener("mouseleave", () => dragging = false);

  canvas.addEventListener("mousemove", (e) => {
    if (dragging && toolSel.value === "pan") {
      const dx = e.offsetX - last.x;
      const dy = e.offsetY - last.y;
      cam.x += dx;
      cam.y += dy;
      last = { x: e.offsetX, y: e.offsetY };
      draw();
    }
  });

  canvas.addEventListener("wheel", (e) => {
    if (toolSel.value !== "pan") return;
    e.preventDefault();
    const zoomFactor = (e.deltaY < 0) ? 1.1 : 0.9;
    const mx = e.offsetX, my = e.offsetY;
    // zoom around mouse
    const before = screenToImage(mx, my);
    cam.zoom = Math.max(0.2, Math.min(5, cam.zoom * zoomFactor));
    const after = screenToImage(mx, my);
    cam.x += (after.x - before.x) * cam.zoom;
    cam.y += (after.y - before.y) * cam.zoom;
    draw();
  }, { passive:false });

  canvas.addEventListener("click", async (e) => {
    const t = toolSel.value;
    const pt = screenToImage(e.offsetX, e.offsetY);

    if (t === "scale") {
      scalePts.push(pt);
      if (scalePts.length === 2) {
        const dx = scalePts[1].x - scalePts[0].x;
        const dy = scalePts[1].y - scalePts[0].y;
        const pxDist = Math.sqrt(dx*dx + dy*dy);
        const m = prompt(`Reale Distanz in Metern (Pixel-Distanz: ${pxDist.toFixed(1)} px):`, "1.0");
        if (m && parseFloat(m) > 0) {
          const scale = (parseFloat(m) / pxDist); // m per px
          const res = await fetch(`/api/plans/${PLAN_ID}/scale`, {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ scale_m_per_px: scale.toString() })
          });
          if (res.ok) {
            scaleText.textContent = scale.toString();
            alert("Maßstab gespeichert.");
          } else {
            alert("Maßstab speichern fehlgeschlagen.");
          }
        }
        scalePts = [];
      }
      draw();
      return;
    }

    if (t === "room") {
      roomPts.push(pt);
      draw();
      return;
    }

    if (t === "point") {
      const payload = {
        point_type: pointTypeSel.value,
        x_px: Math.round(pt.x),
        y_px: Math.round(pt.y),
        attributes: {}
      };
      const res = await fetch(`/api/plans/${PLAN_ID}/points`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      });
      if (!res.ok) { alert("Punkt speichern fehlgeschlagen."); return; }
      location.reload();
      return;
    }
  });

  // init
  setHint();
  img.onload = () => {
    imgLoaded = true;
    // fit to canvas
    const sx = canvas.width / img.width;
    const sy = canvas.height / img.height;
    cam.zoom = Math.min(sx, sy);
    cam.x = (canvas.width - img.width * cam.zoom) / 2;
    cam.y = (canvas.height - img.height * cam.zoom) / 2;
    draw();
  };
  img.src = IMG_URL;
})();
