// config/db.js
const mongoose = require('mongoose');
require('dotenv').config();

const URL = process.env.MONGO_URI;

mongoose
  .connect(URL)
  .then(() => {
    console.log("User database connected");
  })
  .catch((e) => {
    console.log("User database connection error", e);
  });

// User model
const userSchema = new mongoose.Schema({
  // Auth & Identity
  googleId: {
    type: String,
    unique: true,
    sparse: true,
    required: true
  },
  email: {
    type: String,
    unique: true,
    required: true,
    trim: true,
    lowercase: true,
    match: [/\S+@\S+\.\S+/, 'is invalid']
  },
  name: {
    type: String,
    trim: true
  },
  walletAddress: {
    type: String,
    index: true,
    default: null,
    // validate: {
    //   validator: function (v) {
    //     return /^0x[a-fA-F0-9]{40}$/.test(v);
    //   },
    //   message: props => `${props.value} is not a valid wallet address!`
    // }
  },

  // Challenges
  challengesWon: [{
    challengeId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Challenge',
      required: true
    },
    dateCompleted: {
      type: Date,
      default: Date.now
    },
    stakedAmount: {
      type: Number,
      required: true,
      min: 0
    },
    rewardReceived: {
      type: Number,
      required: true,
      min: 0
    }
  }],

  // Activity
  currentStreak: {
    type: Number,
    default: 0,
    min: 0
  },

}, {
  timestamps: true
});



const User = mongoose.model('User', userSchema);




module.exports = { User};


