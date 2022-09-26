/*
 * Freeform Rigging and Animation Tools
 * Copyright (C) 2020  Micah Zahm
 *
 * Freeform Rigging and Animation Tools is free software: you can redistribute it 
 * and/or modify it under the terms of the GNU General Public License as published 
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Freeform Rigging and Animation Tools is distributed in the hope that it will 
 * be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Freeform Rigging and Animation Tools.  
 * If not, see <https://www.gnu.org/licenses/>.
 */


namespace HelixResources.Style
{
    using System;
  using System.Collections;
  using System.Collections.Generic;
  using System.ComponentModel;
    using System.Drawing;
    using System.Globalization;
    using System.IO;
    using System.Linq;
    using System.Runtime.InteropServices;
    using System.Windows;
    using System.Windows.Controls;
    using System.Windows.Data;
    using System.Windows.Interop;
    using System.Windows.Media;
    using System.Windows.Media.Imaging;
    using Freeform.Core.UI;

    public class BindingProxy : Freezable
    {
        #region Overrides of Freezable

        protected override Freezable CreateInstanceCore()
        {
            return new BindingProxy();
        }

        #endregion

        public object Data
        {
            get { return (object)GetValue(DataProperty); }
            set { SetValue(DataProperty, value); }
        }

        // Using a DependencyProperty as the backing store for Data.  This enables animation, styling, binding, etc...
        public static readonly DependencyProperty DataProperty =
            DependencyProperty.Register("Data", typeof(object), typeof(BindingProxy), new UIPropertyMetadata(null));
    }


    public class V1TreeView : TreeView, INotifyPropertyChanged
    {
        public static readonly DependencyProperty SelectedItemsProperty = DependencyProperty.Register("SelectedItem", typeof(object), typeof(V1TreeView), new PropertyMetadata(null));
        public new object SelectedItem
        {
            get { return (object)GetValue(SelectedItemProperty); }
            set
            {
                SetValue(SelectedItemsProperty, value);
                NotifyPropertyChanged("SelectedItem");
            }
        }

        public V1TreeView()
            : base()
        {
            base.SelectedItemChanged += new RoutedPropertyChangedEventHandler<object>(V1TreeView_SelectedItemChanged);
        }

        private void V1TreeView_SelectedItemChanged(object sender, RoutedPropertyChangedEventArgs<object> e)
        {
            this.SelectedItem = base.SelectedItem;
        }

        public event PropertyChangedEventHandler PropertyChanged;
        private void NotifyPropertyChanged(string aPropertyName)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(aPropertyName));
        }
    }


    public class V1MenuItem : INotifyPropertyChanged
    {
        public event EventHandler MenuCommandHandler;

        public RelayCommand MenuCommand { get; set; }

        string _header;
        public string Header
        {
            get { return _header; }
            set
            {
                if (_header != value)
                {
                    _header = value;
                    RaisePropertyChanged("Header");
                }
            }
        }

        string _data;
        public string Data
        {
            get { return _data; }
            set
            {
                if (_data != value)
                {
                    _data = value;
                    RaisePropertyChanged("Data");
                }
            }
        }

        public V1MenuItem()
        {
            MenuCommand = new RelayCommand(MenuCommandCall);
        }

        public void MenuCommandCall(object sender)
        {
            MenuCommandHandler?.Invoke(this, null);
        }

        void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }

  public class MultiSelectionListBox : ListBox
  {
    public static readonly DependencyProperty SelectedItemsListProperty = DependencyProperty.Register(
      "SelectedItemsList",
      typeof(IList),
      typeof(MultiSelectionListBox),
      new PropertyMetadata(null, OnSelectedItemList));

    public IList SelectedItemsList
    {
      get { return (IList)GetValue(SelectedItemsListProperty); }
      set { SetValue(SelectedItemsListProperty, value); }
    }


    public MultiSelectionListBox()
    {
      SelectionChanged += MultiSelectionListBox_SelectionChanged;
    }


    private static void OnSelectedItemList(DependencyObject d, DependencyPropertyChangedEventArgs e)
    {
      MultiSelectionListBox listBox = (MultiSelectionListBox)d;
      IList newItemList = e.NewValue as IList;

      listBox.SetSelectedItems(newItemList);
    }

    void MultiSelectionListBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
      IEnumerable<object> tempListSrc = SelectedItems.Cast<object>();
      List<object> tempListDest = new List<object>();
      tempListDest.AddRange(tempListSrc.ToList());

      SelectedItemsList = tempListDest;
    }
  }


  public class Tabby : HeaderedContentControl
    {
        static Tabby()
        {
            DefaultStyleKeyProperty.OverrideMetadata(typeof(Tabby), new FrameworkPropertyMetadata(typeof(Tabby)));
        }

        public double DogEar
        {
            get { return (double)GetValue(DogEarProperty); }
            set { SetValue(DogEarProperty, value); }
        }

        public static readonly DependencyProperty DogEarProperty =
            DependencyProperty.Register("DogEar",
            typeof(double),
            typeof(Tabby),
            new UIPropertyMetadata(8.0, DogEarPropertyChanged));

        private static void DogEarPropertyChanged(
            DependencyObject obj,
            DependencyPropertyChangedEventArgs e)
        {
            ((Tabby)obj).InvalidateVisual();
        }

        public Tabby()
        {
            SizeChanged += new SizeChangedEventHandler(Tabby_SizeChanged);
        }

        void Tabby_SizeChanged(object sender, SizeChangedEventArgs e)
        {
            var clip = new PathGeometry
            {
                Figures = new PathFigureCollection()
            };
            clip.Figures.Add(
                new PathFigure(
                    new System.Windows.Point(0, 0),
                    new[] {
                    new LineSegment(new System.Windows.Point(ActualWidth - DogEar, 0), true),
                    new LineSegment(new System.Windows.Point(ActualWidth, DogEar), true),
                    new LineSegment(new System.Windows.Point(ActualWidth, ActualHeight), true),
                    new LineSegment(new System.Windows.Point(0, ActualHeight), true) },
                    true)
            );
            Clip = clip;
        }
    }


    public class PercentageConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, System.Globalization.CultureInfo culture)
        {
            return System.Convert.ToDouble(value) * System.Convert.ToDouble(parameter);
        }

        public object ConvertBack(object value, Type targetType, object parameter, System.Globalization.CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }

    public class WidthPercentConverter : IMultiValueConverter
    {
        FrameworkElement myControl;
        object theValue;

        public object Convert(object[] values, System.Type targetType, object parameter, System.Globalization.CultureInfo culture)
        {
            myControl = values[0] as FrameworkElement;
            theValue = values[1];
            double.TryParse(values[1].ToString(), out double v);
            return myControl.Width * v;
        }

        public object[] ConvertBack(object value, System.Type[] targetTypes, object parameter, System.Globalization.CultureInfo culture)
        {
            return new object[] { null, myControl.Name + " : " + theValue };
        }
    }


    public class BooleanAndConverter : IMultiValueConverter
    {
        public object Convert(object[] values, Type targetType, object parameter, System.Globalization.CultureInfo culture)
        {
            foreach (object value in values)
            {
                if ((value is bool) && (bool)value == false)
                {
                    return false;
                }
            }
            return true;
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, System.Globalization.CultureInfo culture)
        {
            throw new NotSupportedException();
        }
    }

    public class BooleanToVisibilityMultiConverter : IMultiValueConverter
    {
        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            return values.OfType<bool>().All(b => b) ? Visibility.Visible : Visibility.Hidden;
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }

    public class StyleConverter : IMultiValueConverter
    {
        public object Convert(object[] values, Type targetType, object parameter, System.Globalization.CultureInfo culture)
        {
            FrameworkElement targetElement = values[0] as FrameworkElement;

            if (!(values[1] is string styleName))
                return null;

            Style newStyle = (Style)targetElement.TryFindResource(styleName);

            if (newStyle == null)
                newStyle = (Style)targetElement.TryFindResource("MyDefaultStyleName");

            return newStyle;
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, System.Globalization.CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }

    [ValueConversion(typeof(bool), typeof(bool))]
    public class InverseBooleanConverter : IValueConverter
    {
        #region IValueConverter Members

        public object Convert(object value, Type targetType, object parameter,
            System.Globalization.CultureInfo culture)
        {
            if (targetType != typeof(bool))
                throw new InvalidOperationException("The target must be a boolean");

            return !(bool)value;
        }

        public object ConvertBack(object value, Type targetType, object parameter,
            System.Globalization.CultureInfo culture)
        {
            throw new NotSupportedException();
        }

        #endregion
    }


    public class IconManager
    {
        // Constants that we need in the function call

        private const int SHGFI_ICON = 0x100;
        private const int SHGFI_LARGEICON = 0x0;
        private const int SHGFI_SMALLICON = 0x1;
        private const int SHIL_EXTRALARGE = 0x2;
        private const int SHIL_JUMBO = 0x4;
        private const int WM_CLOSE = 0x0010;

        // This structure will contain information about the file

        public struct SHFILEINFO
        {
            // Handle to the icon representing the file

            public IntPtr hIcon;

            // Index of the icon within the image list

            public int iIcon;

            // Various attributes of the file

            public uint dwAttributes;

            // Path to the file

            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)] public string szDisplayName;

            // File type

            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 80)] public string szTypeName;
        };

        [DllImport("Kernel32.dll")]
        public static extern Boolean CloseHandle(IntPtr handle);

        private struct IMAGELISTDRAWPARAMS
        {
            public int cbSize;
            public IntPtr himl;
            public int i;
            public IntPtr hdcDst;
            public int x;
            public int y;
            public int cx;
            public int cy;
            public int xBitmap; // x offest from the upperleft of bitmap
            public int yBitmap; // y offset from the upperleft of bitmap
            public int rgbBk;
            public int rgbFg;
            public int fStyle;
            public int dwRop;
            public int fState;
            public int Frame;
            public int crEffect;

            public IMAGELISTDRAWPARAMS(int defaultValue)
            {
                cbSize = defaultValue;
                himl = new IntPtr();
                i = defaultValue;
                hdcDst = new IntPtr();
                x = defaultValue;
                y = defaultValue;
                cx = defaultValue;
                cy = defaultValue;
                xBitmap = defaultValue;
                yBitmap = defaultValue;
                rgbBk = defaultValue;
                rgbFg = defaultValue;
                fStyle = defaultValue;
                dwRop = defaultValue;
                fState = defaultValue;
                Frame = defaultValue;
                crEffect = defaultValue;
            }
        }

        [DllImport("user32")]
        private static extern
        IntPtr SendMessage(
            IntPtr handle,
            int Msg,
            IntPtr wParam,
            IntPtr lParam
            );

        [StructLayout(LayoutKind.Sequential)]
        private struct IMAGEINFO
        {
            private readonly IntPtr hbmImage;
            private readonly IntPtr hbmMask;
            private readonly int Unused1;
            private readonly int Unused2;
            private readonly RECT rcImage;
        }

        #region Private ImageList COM Interop (XP)

        [ComImport]
        [Guid("46EB5926-582E-4017-9FDF-E8998DAA0950")]
        [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        //helpstring("Image List"),
        private interface IImageList
        {
            [PreserveSig]
            int Add(
                IntPtr hbmImage,
                IntPtr hbmMask,
                ref int pi);

            [PreserveSig]
            int ReplaceIcon(
                int i,
                IntPtr hicon,
                ref int pi);

            [PreserveSig]
            int SetOverlayImage(
                int iImage,
                int iOverlay);

            [PreserveSig]
            int Replace(
                int i,
                IntPtr hbmImage,
                IntPtr hbmMask);

            [PreserveSig]
            int AddMasked(
                IntPtr hbmImage,
                int crMask,
                ref int pi);

            [PreserveSig]
            int Draw(
                ref IMAGELISTDRAWPARAMS pimldp);

            [PreserveSig]
            int Remove(
                int i);

            [PreserveSig]
            int GetIcon(
                int i,
                int flags,
                ref IntPtr picon);

            [PreserveSig]
            int GetImageInfo(
                int i,
                ref IMAGEINFO pImageInfo);

            [PreserveSig]
            int Copy(
                int iDst,
                IImageList punkSrc,
                int iSrc,
                int uFlags);

            [PreserveSig]
            int Merge(
                int i1,
                IImageList punk2,
                int i2,
                int dx,
                int dy,
                ref Guid riid,
                ref IntPtr ppv);

            [PreserveSig]
            int Clone(
                ref Guid riid,
                ref IntPtr ppv);

            [PreserveSig]
            int GetImageRect(
                int i,
                ref RECT prc);

            [PreserveSig]
            int GetIconSize(
                ref int cx,
                ref int cy);

            [PreserveSig]
            int SetIconSize(
                int cx,
                int cy);

            [PreserveSig]
            int GetImageCount(
                ref int pi);

            [PreserveSig]
            int SetImageCount(
                int uNewCount);

            [PreserveSig]
            int SetBkColor(
                int clrBk,
                ref int pclr);

            [PreserveSig]
            int GetBkColor(
                ref int pclr);

            [PreserveSig]
            int BeginDrag(
                int iTrack,
                int dxHotspot,
                int dyHotspot);

            [PreserveSig]
            int EndDrag();

            [PreserveSig]
            int DragEnter(
                IntPtr hwndLock,
                int x,
                int y);

            [PreserveSig]
            int DragLeave(
                IntPtr hwndLock);

            [PreserveSig]
            int DragMove(
                int x,
                int y);

            [PreserveSig]
            int SetDragCursorImage(
                ref IImageList punk,
                int iDrag,
                int dxHotspot,
                int dyHotspot);

            [PreserveSig]
            int DragShowNolock(
                int fShow);

            [PreserveSig]
            int GetDragImage(
                ref POINT ppt,
                ref POINT pptHotspot,
                ref Guid riid,
                ref IntPtr ppv);

            [PreserveSig]
            int GetItemFlags(
                int i,
                ref int dwFlags);

            [PreserveSig]
            int GetOverlayImage(
                int iOverlay,
                ref int piIndex);
        };

        #endregion

        ///
        /// SHGetImageList is not exported correctly in XP.  See KB316931
        /// http://support.microsoft.com/default.aspx?scid=kb;EN-US;Q316931
        /// Apparently (and hopefully) ordinal 727 isn't going to change.
        ///
        [DllImport("shell32.dll", EntryPoint = "#727")]
        private static extern int SHGetImageList(
            int iImageList,
            ref Guid riid,
            out IImageList ppv
            );

        // The signature of SHGetFileInfo (located in Shell32.dll)
        [DllImport("Shell32.dll")]
        public static extern int SHGetFileInfo(string pszPath, int dwFileAttributes, ref SHFILEINFO psfi, int cbFileInfo,
                                               uint uFlags);

        [DllImport("Shell32.dll")]
        public static extern int SHGetFileInfo(IntPtr pszPath, uint dwFileAttributes, ref SHFILEINFO psfi,
                                               int cbFileInfo, uint uFlags);

        [DllImport("shell32.dll", SetLastError = true)]
        private static extern int SHGetSpecialFolderLocation(IntPtr hwndOwner, Int32 nFolder, ref IntPtr ppidl);

        [DllImport("user32")]
        public static extern int DestroyIcon(IntPtr hIcon);

        public struct Pair
        {
            public Icon Icon { get; set; }
            public IntPtr IconHandleToDestroy { set; get; }
        }

        public static int DestroyIcon2(IntPtr hIcon)
        {
            return DestroyIcon(hIcon);
        }

        private static BitmapSource IconSource(Icon ic)
        {
            var ic2 = Imaging.CreateBitmapSourceFromHIcon(ic.Handle,
                                                          Int32Rect.Empty,
                                                          BitmapSizeOptions.FromEmptyOptions());
            ic2.Freeze();
            return ic2;
        }

        public static BitmapSource IconPath(string FileName, bool small, bool checkDisk, bool addOverlay)
        {
            var shinfo = new SHFILEINFO();

            const uint SHGFI_USEFILEATTRIBUTES = 0x000000010;
            const uint SHGFI_LINKOVERLAY = 0x000008000;
            uint flags;

            if (small)
                flags = SHGFI_ICON | SHGFI_SMALLICON;
            else
                flags = SHGFI_ICON | SHGFI_LARGEICON;

            if (!checkDisk)
                flags |= SHGFI_USEFILEATTRIBUTES;

            if (addOverlay)
                flags |= SHGFI_LINKOVERLAY;

            var res = SHGetFileInfo(FileName, 0, ref shinfo, Marshal.SizeOf(shinfo), flags);

            if (res == 0)
                throw (new FileNotFoundException());

            var myIcon = Icon.FromHandle(shinfo.hIcon);
            var bs = IconSource(myIcon);

            myIcon.Dispose();
            bs.Freeze(); // importantissimo se no fa memory leak
            DestroyIcon(shinfo.hIcon);
            CloseHandle(shinfo.hIcon);

            return bs;
        }

        public static BitmapSource GetLargeIcon(string FileName, bool jumbo, bool checkDisk)
        {
            var shinfo = new SHFILEINFO();
            const uint SHGFI_USEFILEATTRIBUTES = 0x000000010;
            const uint SHGFI_SYSICONINDEX = 0x4000;
            const int FILE_ATTRIBUTE_NORMAL = 0x80;
            var flags = SHGFI_SYSICONINDEX;

            if (!checkDisk) // This does not seem to work. If I try it, a folder icon is always returned.
                flags |= SHGFI_USEFILEATTRIBUTES;

            var res = SHGetFileInfo(FileName, FILE_ATTRIBUTE_NORMAL, ref shinfo, Marshal.SizeOf(shinfo), flags);

            if (res == 0)
                throw (new FileNotFoundException());

            var iconIndex = shinfo.iIcon;

            // Get the System IImageList object from the Shell:
            var iidImageList = new Guid("46EB5926-582E-4017-9FDF-E8998DAA0950");

            var size = jumbo ? SHIL_JUMBO : SHIL_EXTRALARGE;
            SHGetImageList(size, ref iidImageList, out IImageList iml);
            var hIcon = IntPtr.Zero;
            const int ILD_TRANSPARENT = 1;
            iml.GetIcon(iconIndex, ILD_TRANSPARENT, ref hIcon);

            var myIcon = Icon.FromHandle(hIcon);
            var bs = IconSource(myIcon);

            myIcon.Dispose();
            bs.Freeze(); // very important to avoid memory leak
            DestroyIcon(hIcon);
            SendMessage(hIcon, WM_CLOSE, IntPtr.Zero, IntPtr.Zero);

            return bs;
        }

        [StructLayout(LayoutKind.Sequential)]
        public struct RECT
        {
            private readonly int _Left;
            private readonly int _Top;
            private readonly int _Right;
            private readonly int _Bottom;
        }

        [StructLayout(LayoutKind.Sequential)]
        public struct POINT
        {
            public int X;
            public int Y;

            public POINT(int x, int y)
            {
                X = x;
                Y = y;
            }

            public static implicit operator System.Drawing.Point(POINT p)
            {
                return new System.Drawing.Point(p.X, p.Y);
            }

            public static implicit operator POINT(System.Drawing.Point p)
            {
                return new POINT(p.X, p.Y);
            }
        }
    }
}
