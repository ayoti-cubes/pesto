let graphRef = null;
let currentSensorData = null;

function makeGraph(history, showAnimation = true) {
  try {
    graphRef.destroy();
  } catch (e) {}

  if (history != null) {
    currentSensorData = history
  } else {
    history = currentSensorData
  }

  const ctx = document.getElementById('graphChart');
  const DATA_COUNT = history.length;
  const labels = [];
  for (let i = 0; i < DATA_COUNT; ++i) {
    labels.push(i.toString());
  }

  const datapoints = history.map(x => x.temp * 10).reverse()

  const minGraph = Math.min(...datapoints) - 20
  const maxGraph = Math.max(...datapoints) + 15
  const areaGraph = maxGraph - minGraph
  const humidAreaGraph = (areaGraph / 5) * 3

  const datapointsHumid = (history[0].humid !== null) ? history.map(x => minGraph + ((x.humid * humidAreaGraph) / 100)).reverse() : []

  if (datapoints[0] < 0) {
    document.getElementById('currentSensorDataPadding').style.background = 'rgba(255, 255, 255, 0.3)'
  } else {
    document.getElementById('currentSensorDataPadding').style.background = 'unset'
  }

  const data = {
    labels: labels,
    datasets: [
      {
        label: 'Humidity',
        backgroundColor: 'rgba(147, 197, 253, 0.3)',
        data: datapointsHumid,
        borderColor: "rgb(147 197 253)",
        fill: true,
        tension: 0.45,
        pointRadius: 0
      },
      {
        label: 'Temperature',
        backgroundColor: 'rgba(255, 255, 255, 0.3)',
        data: datapoints,
        borderColor: "#FFFFFF",
        fill: true,
        tension: 0.45,
        pointRadius: 0
      }
    ]
  }

  graphRef = new Chart(ctx, {
    type: 'line',
    data: data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: (showAnimation) ? 1000 : 0
      },
      plugins: {
        legend: {
          display: false
        },
        title: {
          display: false
        }
      },
      scales: {
        x: {
          display: false
        },
        y: {
          display: false,
          min: minGraph,
          max: maxGraph // HIGHEST ELEMENT PLUS AT LEAST TWO
        }
      }
    },
  });
}

function appXData() {
  return {
    init() {
      fetch('/api/sensors')
        .then((response) => response.json())
        .then((data) => {
          this.sensors = data
        })

      fetch('/api/history')
        .then((response) => response.json())
        .then((data) => {
          this.history = data
          this.selectedSensor = Object.keys(data)[0]
          makeGraph(this.history[this.selectedSensor])
        })

      this.refreshLiveData()
    },

    refreshLiveData() {
      this.isFetchingLiveData = true
      fetch('/api/currentsensor')
        .then((response) => response.json())
        .then((data) => {
          this.liveSensorData = data
          this.isFetchingLiveData = false
        })
    },

    selectSensor(sensor) {
      if (this.selectedSensor !== sensor) {
        this.selectedSensor = sensor
        makeGraph(this.history[sensor])
      }
    },

    getLiveSensorData() {
      try {
        if (this.liveSensorData[this.selectedSensor] !== null) {
          return this.liveSensorData[this.selectedSensor]
        } else if (this.history[this.selectedSensor][0] !== null) {
          return this.history[this.selectedSensor][0]
        } else {
          return undefined
        }
      } catch (e) {
        return undefined
      }
    },

    confirmRename() {
      fetch('/api/sensors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: this.sensorToRename, nom: document.getElementById('newSensorName').value })
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status == 'ok') {
            this.sensors[this.sensorToRename].nom = document.getElementById('newSensorName').value
            this.sensorToRename = null
          }
        })
    },

    confirmResetName() {
      fetch('/api/sensors', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: this.sensorToRename })
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status == 'ok') {
            this.sensors[this.sensorToRename].nom = this.sensorToRename
            this.sensorToRename = null
          }
        })
    },

    history: null,
    selectedSensor: null,
    liveSensorData: null,
    sensors: null,
    sensorToRename: null,
    isFetchingLiveData: true
  }
}

// Prevents graph from showing a border on document resize, caused by a bug in Chart.js
// We diable the animation to have an instantaneous refresh
// TODO: Test if it could be fixed with a property or just redrawing the graph without any computation
addEventListener("resize", (event) => { makeGraph(null, false) });