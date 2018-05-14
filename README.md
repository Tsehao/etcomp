# How to start the compiled binary of pupil player / capture locally under ubuntu:

- Get the linux release zip file from https://github.com/pupil-labs/pupil/releases
- unzip the .deb files from it
- run ```dpkg -x pupil_capture_linux_os_x64_v1.6.13.deb /folder/to/be/extracted/to```
- Optional: Copy the file to a more useful directory e.g. ```/net/store/nbp/users/yourRZname```
- go to the folder ```cd /folder/to/be/extracted/to``` and run ```./pupil_player```

# Git
```
git clone https://github.com/behinger/etcomp
git submodule update --init
```
The latter is necessary to get the files from pupillabs, which we partially will make use of.



# NEW INSTALLATION

We have a large list of dependencies. Easiest is to install using:

``` make install ```

You need these packages definitely instaleld:
```
libglew-dev/xenial,now 1.13.0-2 amd64 [installed,automatic]
libglew1.13/xenial,now 1.13.0-2 amd64 [installed,automatic]
libglewmx-dev/xenial,now 1.13.0-2 amd64 [installed]
libglewmx1.13/xenial,now 1.13.0-2 amd64 [installed,automatic]
```

In principle you can also try to compile glew, but I could not manage properly.

Pyedfread also needs a dependencie from SR-research (libedfapi.so), which is not publicly available. Checkout the Sr research forum!

# Python EDFREAD


- go to ```lib/pyedfread```
- make new folder: ```lib```
- copy ```/net/store/nbp/projects/lib/edfread/build/linux64/libedfapi.so``` to ```lib/libedfapi.so```
- make new folder ```include```
- copy ```/net/store/nbp/projects/lib/edfread/*.h``` to ```lib/include/*.h```
- activate your virtualenv
- run ```python setup.py install```


# pip packages
so far, probably missed a few

```
Cython==0.25.2
h5py==2.7.1
ipython==6.3.1
msgpack-python==0.4.8
numpy==1.13.3
pandas==0.20.3
pyedfread==0.1
scipy==0.19.1
spyder==3.2.8
```
# install opencv
- compile opencv3 as pupil-labs
```
  git clone https://github.com/itseez/opencv
  cd opencv
  mkdir build &&  cd build
  cmake -D CMAKE_BUILD_TYPE=RELEASE -D BUILD_TBB=ON -D WITH_TBB=ON -D WITH_CUDA=OFF -D BUILD_opencv_python2=OFF -DBUILD_opencv_python3=ON  -D CMAKE_INSTALL_PREFIX='XXX/opencv-build'
  make -j4
  make install
  
  ```
# isntalling pyav under linux
This one was difficult
- get ffmpeg3 (only v.2 is installed by defaul)
- I used https://launchpad.net/ubuntu/+archive/primary/+files/ffmpeg_3.3.4.orig.tar.xz
- Unzip it
- you likely need yasm, but its straight forward to build
    - `git clone https://github.com/yasm/yasm`
    - `cd yasm`
    - `sh autoconfig.sh`
    - `./configure --prefix=../yasm-build` # or cmake?
    - `make yasm`
    - `make install`
    - `export PATH=$PATH:/net/store/nbp/users/behinger/tmp/pupil_src_test/yasm-build/bin`
    - should be done, I did not have trouble here at all

- run `./configure --prefix=../ffmpeg-build --enable-shared --enable-pic --cc="gcc -m64 -fPIC"  --extra-cflags="-fPIC"
`  (the enabled shared is key, else we later get errors compiling av)
- run `make` and then `make install`
- add the newly build ffmpeg libraries to the pkg-config path: `export PKG_CONFIG_PATH=:folder/to/install/ffmpeg/:$PKG_CONFIG_PATH` 
- in your python3 venv, run "pip install av'
- you always have to add `export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/net/store/nbp/users/behinger/tmp/pupil_src_test/ffmpeg-build/lib/` before import av (you should else get an error `ImportError: libavfilter.so.6: cannot open shared object file: No such file or directory`)
- I often ran into the problem `avformat_open_input` while installing pip av. Not sure what solved this. I cloned the pyav-git, and removed both instances of avformat_open_input (just commented them out). Compiled then successfully, put them back in, and compiled again - now it worked... strange
- start python and type `import av` - if it works, I'm happy for you... took me 2.5h 
